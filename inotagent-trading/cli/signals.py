"""Signal detection CLI — strategy evaluation + intraday execution guards.

Daily indicators (CoinGecko, market-wide) drive the signal: "should I trade?"
Intraday indicators (exchange-specific) guard execution: "is it safe to trade HERE right now?"

Usage:
    python -m cli.signals scan
    python -m cli.signals check --symbol CRO
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from cli import error, output
from core.db import schema, sync_connect
from strategies.momentum import get_strategy


# ── Intraday Execution Guards ────────────────────────────────────────────────
# These use exchange-specific data (Crypto.com 1m candles) to check if the
# execution venue is safe right now. NOT used for signal generation.
# Thresholds are deliberately extreme — only block clearly dangerous conditions.

def _check_intraday_guards(intraday: dict | None, daily: dict) -> list[str]:
    """Check execution venue conditions. Returns block reasons (empty = safe)."""
    if not intraday:
        return []  # No intraday data — can't guard, allow trade

    blocks = []

    # Check data freshness — stale intraday data shouldn't block
    ts = intraday.get("timestamp") or intraday.get("computed_at")
    if ts and isinstance(ts, datetime):
        age_min = (datetime.now(timezone.utc) - ts).total_seconds() / 60
        if age_min > 10:
            return []  # Data > 10 min old, don't use for blocking

    # Guard 1: RSI overbought on execution venue (>75, deliberately high threshold)
    # "Market rallied on this exchange since daily close — wait for pullback"
    rsi = intraday.get("rsi_14")
    if rsi is not None and float(rsi) > 75:
        blocks.append(f"Venue RSI {float(rsi):.1f} > 75 (overbought on exchange)")

    # Guard 2: Spread too wide (>0.5% for CRO, thin liquidity)
    # "Slippage will eat the trade — wait for liquidity to return"
    spread = intraday.get("spread_pct")
    if spread is not None and float(spread) > 0.5:
        blocks.append(f"Venue spread {float(spread):.2f}% > 0.5% (thin liquidity)")

    # Guard 3: Volatility explosion — intraday vol >> daily ATR
    # "Flash crash/pump in progress — circuit breaker"
    intraday_vol = intraday.get("volatility_1h")
    daily_atr = daily.get("atr_14")
    if intraday_vol is not None and daily_atr is not None and float(daily_atr) > 0:
        ratio = float(intraday_vol) / float(daily_atr)
        if ratio > 2.0:
            blocks.append(f"Venue volatility spike: 1h vol/daily ATR = {ratio:.1f}x (circuit breaker)")

    return blocks


# ── Scan Command ─────────────────────────────────────────────────────────────

def cmd_scan(args):
    s = schema()
    signals = []
    no_signal = []
    filters_blocked = []

    with sync_connect() as conn:
        # Portfolio-level filters (market-wide)
        from core.filters import check_btc_filter, check_portfolio_drawdown
        btc_block = check_btc_filter(conn, s)
        dd_block = check_portfolio_drawdown(conn, s)
        if btc_block:
            filters_blocked.append(btc_block)
        if dd_block:
            filters_blocked.append(dd_block)

        # Load active strategies
        cur = conn.execute(
            f"""SELECT s.id, s.name, s.type, s.params, s.paper_mode,
                       a.symbol AS asset, v.code AS venue
                FROM {s}.strategies s
                LEFT JOIN {s}.assets a ON a.id = s.asset_id
                LEFT JOIN {s}.venues v ON v.id = s.venue_id
                WHERE s.is_active = true AND s.is_current = true"""
        )
        strategies = cur.fetchall()

        for strat in strategies:
            strat = dict(strat)
            params = strat["params"] if isinstance(strat["params"], dict) else json.loads(strat["params"])
            asset = strat["asset"]

            if not asset:
                no_signal.append({"strategy": strat["name"], "reason": "No asset configured"})
                continue

            # ── Daily indicators (CoinGecko, market-wide) — drives signal ──
            cur = conn.execute(
                f"""SELECT * FROM {s}.indicators_daily
                    WHERE asset_id = (SELECT id FROM {s}.assets WHERE symbol = %s)
                    ORDER BY date DESC LIMIT 1""",
                (asset,),
            )
            daily = cur.fetchone()
            if not daily:
                no_signal.append({"strategy": strat["name"], "asset": asset, "reason": "No daily TA data"})
                continue
            daily = dict(daily)

            # Merge custom JSONB into daily dict
            custom = daily.pop("custom", None)
            if custom and isinstance(custom, dict):
                daily.update(custom)

            # ── Intraday indicators (exchange, venue-specific) — guards only ──
            cur = conn.execute(
                f"""SELECT * FROM {s}.indicators_intraday
                    WHERE asset_id = (SELECT id FROM {s}.assets WHERE symbol = %s)
                    ORDER BY timestamp DESC LIMIT 1""",
                (asset,),
            )
            intraday_row = cur.fetchone()
            intraday = dict(intraday_row) if intraday_row else None

            # ── Evaluate signal using strategy registry (daily data) ──
            try:
                strategy = get_strategy(strat["type"], params)
                signal = strategy.evaluate_signal(daily, intraday)
            except ValueError:
                no_signal.append({"strategy": strat["name"], "reason": f"Unknown strategy type: {strat['type']}"})
                continue

            if not signal.has_signal or signal.side != "buy":
                reason = f"Low confidence ({signal.confidence:.2f})" if signal.reasons else "No conditions met"
                no_signal.append({"strategy": strat["name"], "asset": asset, "reason": reason})
                continue

            # ── Intraday execution guards (exchange data) — blocks trade ──
            intraday_blocks = _check_intraday_guards(intraday, daily)
            if intraday_blocks:
                no_signal.append({
                    "strategy": strat["name"],
                    "asset": asset,
                    "reason": f"Venue guard: {intraday_blocks[0]}",
                    "signal_was": signal.confidence,
                    "all_guards": intraday_blocks,
                })
                continue

            # ── Fee profitability check ──
            # Ensure expected profit covers round-trip fees
            exit_params = params.get("exit", {})
            price = float(daily.get("close") or 0)

            if price > 0:
                # Look up fees from trading_pairs table
                cur = conn.execute(
                    f"""SELECT tp.maker_fee, tp.taker_fee FROM {s}.trading_pairs tp
                        JOIN {s}.assets a ON a.id = tp.base_asset_id
                        WHERE a.symbol = %s AND tp.is_current = true AND tp.is_active = true
                        LIMIT 1""",
                    (asset,),
                )
                fee_row = cur.fetchone()
                maker_fee = float(fee_row["maker_fee"] or 0) if fee_row else 0.0025
                taker_fee = float(fee_row["taker_fee"] or 0) if fee_row else 0.005
                round_trip_fee_pct = (maker_fee + taker_fee) * 100  # as percentage

                # Expected profit from strategy's take profit or target
                expected_profit_pct = exit_params.get("take_profit_pct", 0)
                if not expected_profit_pct and exit_params.get("exit_target") == "middle":
                    # Mean reversion — estimate from BB width
                    bb_width = daily.get("bb_width")
                    expected_profit_pct = float(bb_width) / 2 if bb_width else 0

                min_profit = params.get("min_profit_after_fees_pct", round_trip_fee_pct * 1.5)

                if expected_profit_pct > 0 and expected_profit_pct <= round_trip_fee_pct:
                    no_signal.append({
                        "strategy": strat["name"],
                        "asset": asset,
                        "reason": f"Unprofitable after fees: target {expected_profit_pct:.2f}% <= fees {round_trip_fee_pct:.2f}%",
                    })
                    continue

            # ── Build actionable signal ──

            suggested = {"side": "buy", "price": price}
            # Stop loss from % or ATR
            if exit_params.get("stop_loss_pct"):
                suggested["stop_loss"] = round(price * (1 - exit_params["stop_loss_pct"] / 100), 8)
            elif exit_params.get("stop_atr_mult") and daily.get("atr_14"):
                suggested["stop_loss"] = round(price - exit_params["stop_atr_mult"] * float(daily["atr_14"]), 8)
            elif exit_params.get("atr_stop_multiplier") and daily.get("atr_14"):
                suggested["stop_loss"] = round(price - exit_params["atr_stop_multiplier"] * float(daily["atr_14"]), 8)
            if exit_params.get("take_profit_pct"):
                suggested["take_profit"] = round(price * (1 + exit_params["take_profit_pct"] / 100), 8)

            signals.append({
                "strategy": strat["name"],
                "asset": asset,
                "venue": strat["venue"],
                "signal": signal.side,
                "confidence": signal.confidence,
                "reasons": signal.reasons,
                "failed_conditions": signal.failed_conditions,
                "indicators": signal.indicators,
                "suggested_action": suggested,
                "intraday_available": intraday is not None,
            })

    # If portfolio filters blocked, move signals to blocked list
    if filters_blocked:
        for sig in signals:
            sig["blocked_by"] = filters_blocked
        output({"signals": [], "blocked": signals, "no_signal": no_signal, "filters": filters_blocked})
    else:
        output({"signals": signals, "no_signal": no_signal, "filters": []})


# ── Check Command ────────────────────────────────────────────────────────────

def cmd_check(args):
    """Detailed analysis for one asset — shows daily + intraday + guard status."""
    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(
            f"""SELECT * FROM {s}.indicators_daily
                WHERE asset_id = (SELECT id FROM {s}.assets WHERE symbol = %s)
                ORDER BY date DESC LIMIT 1""",
            (args.symbol.upper(),),
        )
        daily = cur.fetchone()
        daily_dict = dict(daily) if daily else {}

        cur = conn.execute(
            f"""SELECT * FROM {s}.indicators_intraday
                WHERE asset_id = (SELECT id FROM {s}.assets WHERE symbol = %s)
                ORDER BY timestamp DESC LIMIT 1""",
            (args.symbol.upper(),),
        )
        intraday = cur.fetchone()
        intraday_dict = dict(intraday) if intraday else None

        guards = _check_intraday_guards(intraday_dict, daily_dict)

    result = {
        "symbol": args.symbol.upper(),
        "daily": daily_dict or None,
        "intraday": intraday_dict,
        "venue_guards": guards if guards else "OK",
    }

    if intraday_dict and intraday_dict.get("timestamp"):
        ts = intraday_dict["timestamp"]
        if isinstance(ts, datetime):
            result["intraday_age_minutes"] = round((datetime.now(timezone.utc) - ts).total_seconds() / 60, 1)

    output(result)


def main():
    parser = argparse.ArgumentParser(prog="python -m cli.signals", description="Signal detection CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("scan")

    p = sub.add_parser("check")
    p.add_argument("--symbol", required=True)

    args = parser.parse_args()
    commands = {"scan": cmd_scan, "check": cmd_check}
    commands[args.command](args)


if __name__ == "__main__":
    main()
