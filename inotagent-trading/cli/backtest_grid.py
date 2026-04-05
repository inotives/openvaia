"""DCA Grid backtester — simulates grid cycles on historical OHLCV data.

Different from signal backtester (cli/backtest.py):
- Simulates multiple limit orders per cycle
- Uses daily high/low to detect fills (not just close)
- Tracks grid cycle lifecycle: open → fill → TP → close

Usage:
    python -m cli.backtest_grid run --strategy btc_dca_grid --from 2025-01-01 --to 2026-03-31
    python -m cli.backtest_grid run --strategy btc_dca_grid --from 2025-01-01 --to 2026-03-31 --capital 1000
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import date, datetime
from decimal import Decimal

from cli import error, output
from core.db import schema, sync_connect
from strategies.dca_grid import (
    compute_batch_tp_price,
    compute_fifo_tp_price,
    compute_grid_levels,
    get_volatility_regime,
    get_grid_params,
    select_grid_mode,
    should_open_cycle,
    GridLevel,
)


def _run_grid_backtest(
    conn, s: str, strategy_name: str, params: dict,
    asset_id: int, date_from: date, date_to: date,
    initial_capital: float, maker_fee: float = 0.0024,
) -> dict:
    """Execute a grid backtest over historical data."""
    start_time = time.monotonic()

    # Load daily OHLCV + indicators
    cur = conn.execute(
        f"""SELECT d.date, d.open, d.high, d.low, d.close, d.volume,
                   i.rsi_14, i.atr_14, i.regime_score
            FROM {s}.ohlcv_daily d
            JOIN LATERAL (
                SELECT rsi_14, atr_14, regime_score FROM {s}.indicators_daily
                WHERE asset_id = d.asset_id AND date = d.date LIMIT 1
            ) i ON true
            WHERE d.asset_id = %s AND d.date BETWEEN %s AND %s
            ORDER BY d.date""",
        (asset_id, date_from, date_to),
    )
    days = [dict(r) for r in cur.fetchall()]

    if len(days) < 30:
        return {"error": f"Insufficient data: {len(days)} days (need at least 30)"}

    # Simulation state
    cash = initial_capital
    cycles_completed = []
    active_cycle = None
    cooldown_until = None
    expired_pending = []
    total_fees = 0.0

    entry_params = params.get("entry", {})
    exit_params = params.get("exit", {})
    grid_params = params.get("grid", {})
    mode_params = params.get("mode", {})
    position_params = params.get("position", {})
    cooldown_min = exit_params.get("cooldown_minutes", 30)
    max_cycle_hours = exit_params.get("max_cycle_duration_hours", 72)
    max_expired = exit_params.get("max_expired_pending_per_asset", 2)
    capital_pct = position_params.get("capital_per_cycle_pct", 10) / 100
    pause_threshold = mode_params.get("regime_pause_threshold", 65)
    resume_threshold = mode_params.get("regime_resume_threshold", 55)

    grid_paused = False  # regime above pause threshold

    for day_idx, day in enumerate(days):
        close = float(day["close"])
        high = float(day["high"])
        low = float(day["low"])
        rsi = float(day["rsi_14"]) if day["rsi_14"] else None
        atr = float(day["atr_14"]) if day["atr_14"] else None
        regime = float(day["regime_score"]) if day["regime_score"] else 50

        if not atr or close <= 0:
            continue

        atr_pct = atr / close * 100

        # ── Regime transition ──
        if regime >= pause_threshold:
            if not grid_paused and active_cycle:
                # Cancel unfilled (return capital), keep filled TPs
                for lvl in active_cycle["levels"]:
                    if lvl["status"] == "open":
                        cash += lvl["capital"]
                        lvl["status"] = "cancelled"
                active_cycle["status"] = "transition_pending"
                expired_pending.append(active_cycle)
                active_cycle = None
            grid_paused = True
        elif regime < resume_threshold:
            grid_paused = False

        # ── Check active cycle fills ──
        if active_cycle and active_cycle["status"] == "active":
            for lvl in active_cycle["levels"]:
                if lvl["status"] != "open":
                    continue
                # Level fills if daily low reached the grid price
                if low <= lvl["price"]:
                    lvl["status"] = "filled"
                    lvl["fill_day"] = str(day["date"])
                    fee = lvl["capital"] * maker_fee
                    total_fees += fee

            # Check batch TP
            filled = [l for l in active_cycle["levels"] if l["status"] == "filled"]
            if filled and active_cycle["mode"] == "batch":
                total_cost = sum(l["capital"] for l in filled)
                total_qty = sum(l["quantity"] for l in filled)
                if total_qty > 0:
                    avg_entry = total_cost / total_qty
                    vol = get_volatility_regime(atr_pct)
                    _, profit_target = get_grid_params(vol, params)
                    tp_price = avg_entry * (1 + profit_target / 100 + maker_fee)
                    active_cycle["tp_price"] = tp_price

                    if high >= tp_price:
                        # Batch TP filled
                        proceeds = total_qty * tp_price
                        sell_fee = proceeds * maker_fee
                        total_fees += sell_fee
                        profit = proceeds - total_cost - sell_fee
                        cash += total_cost + profit
                        # Return unfilled capital
                        for l in active_cycle["levels"]:
                            if l["status"] == "open":
                                cash += l["capital"]
                                l["status"] = "cancelled"
                        active_cycle["status"] = "closed"
                        active_cycle["close_reason"] = "batch_tp"
                        active_cycle["profit"] = profit
                        active_cycle["close_day"] = str(day["date"])
                        cycles_completed.append(active_cycle)
                        active_cycle = None
                        continue

            # Check FIFO TPs
            if filled and active_cycle and active_cycle["mode"] == "adaptive_fifo":
                vol = get_volatility_regime(atr_pct)
                _, profit_target = get_grid_params(vol, params)

                for lvl in active_cycle["levels"]:
                    if lvl["status"] != "filled":
                        continue
                    tp = lvl["price"] * (1 + profit_target / 100 + maker_fee)
                    if high >= tp:
                        proceeds = lvl["quantity"] * tp
                        sell_fee = proceeds * maker_fee
                        total_fees += sell_fee
                        profit = proceeds - lvl["capital"] - sell_fee
                        cash += lvl["capital"] + profit
                        lvl["status"] = "sold"
                        lvl["profit"] = profit

                # All sold?
                filled_or_sold = [l for l in active_cycle["levels"] if l["status"] in ("filled", "sold")]
                if filled_or_sold and all(l["status"] == "sold" for l in filled_or_sold):
                    # Return unfilled capital to cash
                    for l in active_cycle["levels"]:
                        if l["status"] == "open":
                            cash += l["capital"]
                            l["status"] = "cancelled"
                    total_profit = sum(l.get("profit", 0) for l in active_cycle["levels"] if l.get("profit"))
                    active_cycle["status"] = "closed"
                    active_cycle["close_reason"] = "all_fifo_tps"
                    active_cycle["profit"] = total_profit
                    active_cycle["close_day"] = str(day["date"])
                    cycles_completed.append(active_cycle)
                    active_cycle = None
                    continue

            # Check stop-loss
            if active_cycle and active_cycle.get("stop_loss"):
                if low <= active_cycle["stop_loss"]:
                    filled = [l for l in active_cycle["levels"] if l["status"] == "filled"]
                    total_cost = sum(l["capital"] for l in filled)
                    total_qty = sum(l["quantity"] for l in filled)
                    if total_qty > 0:
                        proceeds = total_qty * active_cycle["stop_loss"]
                        sell_fee = proceeds * maker_fee
                        total_fees += sell_fee
                        loss = proceeds - total_cost - sell_fee
                        cash += total_cost + loss
                    for l in active_cycle["levels"]:
                        if l["status"] == "open":
                            cash += l["capital"]
                            l["status"] = "cancelled"
                    active_cycle["status"] = "closed"
                    active_cycle["close_reason"] = "stop_loss"
                    active_cycle["profit"] = loss if total_qty > 0 else 0
                    active_cycle["close_day"] = str(day["date"])
                    cycles_completed.append(active_cycle)
                    active_cycle = None
                    continue

            # Check expiry (72h ≈ 3 days in daily backtest)
            if active_cycle and active_cycle.get("open_day_idx") is not None:
                days_open = day_idx - active_cycle["open_day_idx"]
                if days_open >= max_cycle_hours / 24:
                    for l in active_cycle["levels"]:
                        if l["status"] == "open":
                            cash += l["capital"]
                            l["status"] = "cancelled"
                    active_cycle["status"] = "expired_pending"
                    expired_pending.append(active_cycle)
                    active_cycle = None

        # ── Check expired_pending TPs ──
        for exp_cycle in list(expired_pending):
            for lvl in exp_cycle["levels"]:
                if lvl["status"] == "filled":
                    vol = get_volatility_regime(atr_pct)
                    _, profit_target = get_grid_params(vol, params)
                    tp = lvl["price"] * (1 + profit_target / 100 + maker_fee)
                    if high >= tp:
                        proceeds = lvl["quantity"] * tp
                        sell_fee = proceeds * maker_fee
                        total_fees += sell_fee
                        profit = proceeds - lvl["capital"] - sell_fee
                        cash += lvl["capital"] + profit
                        lvl["status"] = "sold"
                        lvl["profit"] = profit

            # Check if all resolved
            remaining = [l for l in exp_cycle["levels"] if l["status"] == "filled"]
            if not remaining:
                total_profit = sum(l.get("profit", 0) for l in exp_cycle["levels"] if l.get("profit"))
                exp_cycle["status"] = "closed"
                exp_cycle["close_reason"] = "expired_tps_filled"
                exp_cycle["profit"] = total_profit
                exp_cycle["close_day"] = str(day["date"])
                cycles_completed.append(exp_cycle)
                expired_pending.remove(exp_cycle)

        # ── Open new cycle ──
        if not active_cycle and not grid_paused:
            can_open, _, is_defensive = should_open_cycle(
                regime, rsi, atr_pct, False, len(expired_pending), params
            )

            if can_open:
                cycle_capital = cash * capital_pct
                if cycle_capital < 5:  # min viable
                    continue

                cash -= cycle_capital

                levels, stop_loss, profit_target = compute_grid_levels(
                    Decimal(str(close)), Decimal(str(atr)),
                    Decimal(str(cycle_capital)), params,
                    Decimal(str(maker_fee)),
                )

                if not levels:
                    cash += cycle_capital
                    continue

                mode = select_grid_mode(regime, params)

                active_cycle = {
                    "mode": mode,
                    "levels": [
                        {"level": l.level, "price": float(l.price), "capital": float(l.capital),
                         "quantity": float(l.quantity), "status": "open"}
                        for l in levels
                    ],
                    "stop_loss": float(stop_loss),
                    "status": "active",
                    "open_day": str(day["date"]),
                    "open_day_idx": day_idx,
                    "defensive": is_defensive,
                }

    # Close any remaining active cycle at last price
    if active_cycle:
        filled = [l for l in active_cycle["levels"] if l["status"] == "filled"]
        total_cost = sum(l["capital"] for l in filled)
        total_qty = sum(l["quantity"] for l in filled)
        if total_qty > 0:
            last_close = float(days[-1]["close"])
            proceeds = total_qty * last_close
            loss = proceeds - total_cost
            cash += total_cost + loss
        else:
            cash += sum(l["capital"] for l in active_cycle["levels"] if l["status"] == "open")
        active_cycle["status"] = "closed"
        active_cycle["close_reason"] = "end_of_period"
        active_cycle["close_day"] = str(days[-1]["date"])
        cycles_completed.append(active_cycle)

    # Same for expired pending
    for exp in expired_pending:
        filled = [l for l in exp["levels"] if l["status"] == "filled"]
        total_cost = sum(l["capital"] for l in filled)
        total_qty = sum(l["quantity"] for l in filled)
        if total_qty > 0:
            last_close = float(days[-1]["close"])
            proceeds = total_qty * last_close
            loss = proceeds - total_cost
            cash += total_cost + loss
        exp["status"] = "closed"
        exp["close_reason"] = "end_of_period"
        cycles_completed.append(exp)

    # Compute results
    final_value = cash
    total_return = final_value - initial_capital
    total_return_pct = total_return / initial_capital * 100

    first_close = float(days[0]["close"])
    last_close = float(days[-1]["close"])
    hodl_return_pct = (last_close - first_close) / first_close * 100

    wins = [c for c in cycles_completed if c.get("profit", 0) > 0]
    losses = [c for c in cycles_completed if c.get("profit", 0) <= 0 and c.get("close_reason") != "end_of_period"]

    run_duration = int((time.monotonic() - start_time) * 1000)

    return {
        "strategy": strategy_name,
        "period": f"{date_from} to {date_to} ({len(days)} days)",
        "initial_capital": initial_capital,
        "final_value": round(final_value, 2),
        "performance": {
            "total_return_pct": round(total_return_pct, 4),
            "total_return_usd": round(total_return, 2),
            "hodl_return_pct": round(hodl_return_pct, 4),
            "alpha_pct": round(total_return_pct - hodl_return_pct, 4),
            "total_fees": round(total_fees, 2),
        },
        "cycles": {
            "total": len(cycles_completed),
            "winning": len(wins),
            "losing": len(losses),
            "win_rate": round(len(wins) / len(cycles_completed), 4) if cycles_completed else 0,
            "avg_profit": round(sum(c.get("profit", 0) for c in wins) / len(wins), 2) if wins else 0,
            "avg_loss": round(sum(c.get("profit", 0) for c in losses) / len(losses), 2) if losses else 0,
            "batch_cycles": len([c for c in cycles_completed if c.get("mode") == "batch"]),
            "fifo_cycles": len([c for c in cycles_completed if c.get("mode") == "adaptive_fifo"]),
            "stop_losses": len([c for c in cycles_completed if c.get("close_reason") == "stop_loss"]),
            "expired": len([c for c in cycles_completed if "expired" in (c.get("close_reason") or "")]),
        },
        "run_duration_ms": run_duration,
    }


def cmd_run(args):
    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(
            f"""SELECT s.*, a.id AS resolved_asset_id
                FROM {s}.strategies s
                LEFT JOIN {s}.assets a ON a.id = s.asset_id
                WHERE s.name = %s AND s.is_current = true""",
            (args.strategy,),
        )
        strat = cur.fetchone()
        if not strat:
            error(f"Strategy '{args.strategy}' not found")
        strat = dict(strat)
        params = strat["params"] if isinstance(strat["params"], dict) else json.loads(strat["params"])

        # Get maker fee
        cur = conn.execute(
            f"""SELECT maker_fee FROM {s}.trading_pairs
                WHERE base_asset_id = %s AND is_current = true AND pair_symbol NOT LIKE '%%:%%'
                LIMIT 1""",
            (strat["resolved_asset_id"],),
        )
        fee_row = cur.fetchone()
        maker_fee = float(fee_row["maker_fee"]) if fee_row and fee_row["maker_fee"] else 0.0024

        result = _run_grid_backtest(
            conn, s, strat["name"], params,
            strat["resolved_asset_id"], args.date_from, args.date_to,
            args.capital, maker_fee,
        )

    output(result)


def main():
    parser = argparse.ArgumentParser(prog="python -m cli.backtest_grid", description="DCA Grid backtester")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("run")
    p.add_argument("--strategy", required=True)
    p.add_argument("--from", dest="date_from", type=date.fromisoformat, required=True)
    p.add_argument("--to", dest="date_to", type=date.fromisoformat, required=True)
    p.add_argument("--capital", type=float, default=1000)

    args = parser.parse_args()
    commands = {"run": cmd_run}
    commands[args.command](args)


if __name__ == "__main__":
    main()
