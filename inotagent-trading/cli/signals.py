"""Signal detection CLI — rules engine + confidence scoring.

Usage:
    python -m cli.signals scan
    python -m cli.signals check --symbol CRO
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal

from cli import error, output
from core.db import schema, sync_connect


def _evaluate_momentum(params: dict, daily: dict, intraday: dict | None) -> tuple[list, list, dict]:
    """Evaluate momentum strategy conditions. Returns (reasons, failed, indicators)."""
    entry = params.get("entry", {})
    reasons = []
    failed = []
    indicators = {}

    # RSI
    rsi = daily.get("rsi_14")
    if rsi is not None:
        indicators["rsi_14"] = float(rsi)
        threshold = entry.get("rsi_buy_threshold", 30)
        if rsi < threshold:
            reasons.append(f"RSI(14) = {rsi:.1f} < {threshold} (oversold)")
        else:
            failed.append(f"RSI(14) = {rsi:.1f} >= {threshold}")

    # EMA crossover
    if intraday:
        ema_fast = intraday.get("ema_9")
        ema_slow = intraday.get("ema_21")
        if ema_fast is not None and ema_slow is not None:
            indicators["ema_9"] = float(ema_fast)
            indicators["ema_21"] = float(ema_slow)
            if ema_fast > ema_slow:
                reasons.append("EMA(9) > EMA(21) (bullish)")
            else:
                failed.append("EMA(9) <= EMA(21) (no crossover)")

    # ADX
    adx = daily.get("adx_14")
    if adx is not None:
        indicators["adx_14"] = float(adx)
        min_adx = entry.get("min_adx", 25)
        if adx > min_adx:
            reasons.append(f"ADX(14) = {adx:.1f} > {min_adx} (strong trend)")
        else:
            failed.append(f"ADX(14) = {adx:.1f} <= {min_adx} (weak trend)")

    # Volume ratio
    if intraday:
        vol_ratio = intraday.get("volume_ratio")
        if vol_ratio is not None:
            indicators["volume_ratio"] = float(vol_ratio)
            min_vol = entry.get("volume_ratio_min", 1.5)
            if vol_ratio > min_vol:
                reasons.append(f"Volume ratio = {vol_ratio:.1f} > {min_vol}")
            else:
                failed.append(f"Volume ratio = {vol_ratio:.1f} <= {min_vol}")

    # Regime score
    regime = daily.get("regime_score")
    if regime is not None:
        indicators["regime_score"] = float(regime)
        min_regime = entry.get("min_regime_score", 61)
        if regime > min_regime:
            reasons.append(f"Regime = {regime:.0f} > {min_regime}")
        else:
            failed.append(f"Regime = {regime:.0f} <= {min_regime}")

    return reasons, failed, indicators


def _compute_confidence(reasons: list, failed: list, params: dict) -> float:
    """Weighted confidence score."""
    weights = params.get("entry", {}).get("condition_weights", {})
    total = len(reasons) + len(failed)
    if total == 0:
        return 0.0

    if weights:
        met_weight = sum(weights.get(r.split("(")[0].strip().lower(), 1) for r in reasons)
        total_weight = met_weight + sum(weights.get(f.split("(")[0].strip().lower(), 1) for f in failed)
        return met_weight / total_weight if total_weight > 0 else 0.0

    return len(reasons) / total


def cmd_scan(args):
    s = schema()
    signals = []
    no_signal = []

    with sync_connect() as conn:
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

            # Fetch latest daily indicators
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

            # Fetch latest intraday indicators
            cur = conn.execute(
                f"""SELECT * FROM {s}.indicators_intraday
                    WHERE asset_id = (SELECT id FROM {s}.assets WHERE symbol = %s)
                    ORDER BY timestamp DESC LIMIT 1""",
                (asset,),
            )
            intraday_row = cur.fetchone()
            intraday = dict(intraday_row) if intraday_row else None

            # Evaluate based on strategy type
            if strat["type"] == "momentum":
                reasons, failed, indicators = _evaluate_momentum(params, daily, intraday)
            else:
                no_signal.append({"strategy": strat["name"], "reason": f"Unknown type: {strat['type']}"})
                continue

            confidence = _compute_confidence(reasons, failed, params)

            if confidence >= 0.50 and len(reasons) > 0:
                # Build suggested action
                exit_params = params.get("exit", {})
                position_params = params.get("position", {})
                price = float(daily.get("close") or daily.get("ema_9") or 0)

                suggested = {
                    "side": "buy",
                    "price": price,
                }
                if exit_params.get("stop_loss_pct"):
                    suggested["stop_loss"] = round(price * (1 - exit_params["stop_loss_pct"] / 100), 8)
                if exit_params.get("take_profit_pct"):
                    suggested["take_profit"] = round(price * (1 + exit_params["take_profit_pct"] / 100), 8)

                signals.append({
                    "strategy": strat["name"],
                    "asset": asset,
                    "venue": strat["venue"],
                    "signal": "buy",
                    "confidence": round(confidence, 4),
                    "reasons": reasons,
                    "failed_conditions": failed,
                    "indicators": indicators,
                    "suggested_action": suggested,
                })
            else:
                no_signal.append({
                    "strategy": strat["name"],
                    "asset": asset,
                    "reason": f"Low confidence ({confidence:.2f})" if reasons else "No conditions met",
                })

    output({"signals": signals, "no_signal": no_signal})


def cmd_check(args):
    """Detailed signal analysis for one asset."""
    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(
            f"""SELECT * FROM {s}.indicators_daily
                WHERE asset_id = (SELECT id FROM {s}.assets WHERE symbol = %s)
                ORDER BY date DESC LIMIT 1""",
            (args.symbol.upper(),),
        )
        daily = cur.fetchone()

        cur = conn.execute(
            f"""SELECT * FROM {s}.indicators_intraday
                WHERE asset_id = (SELECT id FROM {s}.assets WHERE symbol = %s)
                ORDER BY timestamp DESC LIMIT 1""",
            (args.symbol.upper(),),
        )
        intraday = cur.fetchone()

    output({
        "symbol": args.symbol.upper(),
        "daily": dict(daily) if daily else None,
        "intraday": dict(intraday) if intraday else None,
    })


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
