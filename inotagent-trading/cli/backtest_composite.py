"""Composite backtester — regime-based strategy switching on historical data.

Simulates the full trading system:
  RS 0–65:  DCA Grid (ranging/bear market)
  RS 65+:   Pyramid Trend (BTC/ETH) or Trend Follow (SOL/XRP)

Tracks capital across regime transitions, including partial positions.

Usage:
    python -m cli.backtest_composite run --asset BTC --from 2024-06-01 --to 2026-03-31 --capital 1000
    python -m cli.backtest_composite run --asset ETH --from 2024-06-01 --to 2026-03-31 --capital 1000
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import date
from decimal import Decimal

from cli import error, output
from core.db import schema, sync_connect
from strategies.momentum import get_strategy
from strategies.dca_grid import (
    compute_grid_levels, get_volatility_regime, get_grid_params,
    select_grid_mode, should_open_cycle,
)
from strategies.pyramid_trend import PyramidTrendStrategy, PyramidLot


# ── Which trend strategy per asset ───────────────────────────────────────────
TREND_STRATEGY_TYPE = {
    "BTC": "pyramid_trend",
    "ETH": "pyramid_trend",
    "SOL": None,            # Grid-only — trend follow bleeds on SOL
    "XRP": "trend_follow",
}


def _load_daily_data(conn, s, asset_id, date_from, date_to):
    """Load full daily indicators + OHLCV."""
    cur = conn.execute(
        f"""SELECT i.date, i.rsi_14, i.rsi_7, i.ema_9, i.ema_20, i.ema_50, i.ema_200,
                   i.sma_50, i.sma_200, i.macd, i.macd_signal, i.macd_hist,
                   i.atr_14, i.bb_upper, i.bb_lower, i.bb_width, i.adx_14,
                   i.obv, i.volume_sma_20, i.volume_ratio, i.regime_score,
                   i.custom,
                   d.open, d.high, d.low, d.close, d.volume
            FROM {s}.indicators_daily i
            JOIN LATERAL (
                SELECT open, high, low, close, volume FROM {s}.ohlcv_daily
                WHERE asset_id = i.asset_id AND date = i.date
                ORDER BY venue_id LIMIT 1
            ) d ON true
            WHERE i.asset_id = %s AND i.date BETWEEN %s AND %s
            ORDER BY i.date""",
        (asset_id, date_from, date_to),
    )
    return [dict(r) for r in cur.fetchall()]


def _build_indicators(days, i, day):
    """Build indicator dict from day data (shared logic)."""
    indicators = {k: float(v) if v is not None else None for k, v in day.items()
                  if k not in ("date", "open", "high", "low", "volume", "custom")}
    custom = day.get("custom")
    if custom and isinstance(custom, dict):
        for k, v in custom.items():
            if v is not None:
                indicators[k] = float(v)
    if i >= 5:
        indicators["high_5d"] = max(float(days[j]["high"]) for j in range(i - 5, i))
    return indicators


def _run_composite(
    conn, s, asset_symbol, asset_id,
    grid_params, trend_params, trend_type,
    days, initial_capital, maker_fee=0.0024,
    compound=True,
):
    """Run composite regime-switching backtest."""
    start_time = time.monotonic()

    if len(days) < 30:
        return {"error": f"Insufficient data: {len(days)} days"}

    first_close = float(days[0]["close"])
    last_close = float(days[-1]["close"])

    # ── Shared state ──
    cash = initial_capital
    equity_curve = []
    peak_value = initial_capital
    max_drawdown = 0.0
    max_dd_duration = 0
    dd_start = None
    all_trades = []
    trade_num = 0
    regime_log = []  # track regime transitions

    slip = 0.001  # 0.1% slippage
    taker_fee = 0.005

    # ── Grid state ──
    grid_active_cycle = None
    grid_expired_pending = []
    grid_paused = False
    grid_cycles_completed = []
    grid_total_fees = 0.0
    grid_entry_params = grid_params.get("entry", {})
    grid_exit_params = grid_params.get("exit", {})
    grid_mode_params = grid_params.get("mode", {})
    grid_position_params = grid_params.get("position", {})
    grid_capital_pct = grid_position_params.get("capital_per_cycle_pct", 10) / 100
    grid_max_cycle_hours = grid_exit_params.get("max_cycle_duration_hours", 72)
    grid_pause_threshold = grid_mode_params.get("regime_pause_threshold", 65)
    grid_resume_threshold = grid_mode_params.get("regime_resume_threshold", 55)

    # ── Trend state ──
    grid_only = trend_type is None  # No trend strategy — grid handles all regimes
    trend_strategy = get_strategy(trend_type, trend_params) if not grid_only else None
    is_pyramid = trend_type == "pyramid_trend"

    # Trend follow state
    tf_position_qty = 0.0
    tf_entry_price = 0.0
    tf_highest = 0.0

    # Pyramid state
    py_lots = {}
    py_base_entry = 0.0
    py_in_position = False
    py_cooldown = 0
    if is_pyramid:
        allocations = trend_strategy.get_lot_allocations()
        py_lots = {label: PyramidLot(label=label, allocation_pct=alloc)
                   for label, alloc in allocations.items()}

    trend_total_alloc_pct = trend_params.get("position", {}).get("capital_per_trade_pct", 20) / 100

    # ── Current regime mode ──
    current_mode = "grid"  # "grid" or "trend"

    for i, day in enumerate(days):
        close = float(day["close"])
        high = float(day["high"])
        low = float(day["low"])
        rsi = float(day["rsi_14"]) if day["rsi_14"] else None
        atr = float(day["atr_14"]) if day["atr_14"] else None
        regime = float(day["regime_score"]) if day["regime_score"] else 50
        open_price = float(days[i + 1]["open"]) if i + 1 < len(days) else close

        if not atr or close <= 0:
            continue

        atr_pct = atr / close * 100
        indicators = _build_indicators(days, i, day)

        # ═══════════════════════════════════════════════════════════
        # REGIME TRANSITION
        # ═══════════════════════════════════════════════════════════
        prev_mode = current_mode

        if grid_only:
            current_mode = "grid"  # Never switch to trend
        elif regime >= grid_pause_threshold:
            current_mode = "trend"
        elif regime < grid_resume_threshold:
            current_mode = "grid"
        # Between resume and pause: keep current mode (hysteresis)

        if current_mode != prev_mode:
            regime_log.append({
                "date": str(day["date"]),
                "from": prev_mode,
                "to": current_mode,
                "regime_score": regime,
            })

            # ── Transition: grid → trend ──
            if prev_mode == "grid" and current_mode == "trend":
                # Cancel unfilled grid levels, keep filled TPs in expired_pending
                if grid_active_cycle:
                    for lvl in grid_active_cycle["levels"]:
                        if lvl["status"] == "open":
                            cash += lvl["capital"]
                            lvl["status"] = "cancelled"
                    grid_active_cycle["status"] = "transition_pending"
                    grid_expired_pending.append(grid_active_cycle)
                    grid_active_cycle = None
                grid_paused = True

            # ── Transition: trend → grid ──
            elif prev_mode == "trend" and current_mode == "grid":
                grid_paused = False
                # Close trend positions
                if is_pyramid:
                    for label in ["D", "C", "B", "A"]:
                        lot = py_lots[label]
                        if not lot.is_open:
                            continue
                        fill = close * (1 - slip)
                        proceeds = lot.quantity * fill
                        fees = proceeds * taker_fee
                        cost = lot.cost_basis
                        pnl = proceeds - cost - fees
                        cash += proceeds - fees
                        trade_num += 1
                        all_trades.append({
                            "trade_num": trade_num, "strategy": "pyramid_trend",
                            "lot": label, "entry_date": lot.entry_date,
                            "exit_date": str(day["date"]), "entry_price": lot.entry_price,
                            "exit_price": fill, "pnl_usd": pnl,
                            "pnl_pct": (pnl / cost * 100) if cost > 0 else 0,
                            "exit_reason": "regime_transition",
                        })
                        lot.is_open = False
                        lot.quantity = 0.0
                        lot.entry_price = 0.0
                    py_in_position = False
                    py_base_entry = 0.0
                else:
                    if tf_position_qty > 0:
                        fill = close * (1 - slip)
                        proceeds = tf_position_qty * fill
                        fees = proceeds * taker_fee
                        cost = tf_position_qty * tf_entry_price
                        pnl = proceeds - cost - fees
                        cash += proceeds - fees
                        trade_num += 1
                        all_trades.append({
                            "trade_num": trade_num, "strategy": "trend_follow",
                            "entry_price": tf_entry_price, "exit_price": fill,
                            "exit_date": str(day["date"]),
                            "pnl_usd": pnl,
                            "pnl_pct": (pnl / cost * 100) if cost > 0 else 0,
                            "exit_reason": "regime_transition",
                        })
                        tf_position_qty = 0.0
                        tf_entry_price = 0.0
                        tf_highest = 0.0

        # ═══════════════════════════════════════════════════════════
        # GRID MODE (RS < 65)
        # ═══════════════════════════════════════════════════════════
        if current_mode == "grid":
            # ── Check active grid cycle fills ──
            if grid_active_cycle and grid_active_cycle["status"] == "active":
                for lvl in grid_active_cycle["levels"]:
                    if lvl["status"] == "open" and low <= lvl["price"]:
                        lvl["status"] = "filled"
                        fee = lvl["capital"] * maker_fee
                        grid_total_fees += fee

                filled = [l for l in grid_active_cycle["levels"] if l["status"] == "filled"]

                # Batch TP
                if filled and grid_active_cycle["mode"] == "batch":
                    total_cost = sum(l["capital"] for l in filled)
                    total_qty = sum(l["quantity"] for l in filled)
                    if total_qty > 0:
                        avg_entry = total_cost / total_qty
                        vol = get_volatility_regime(atr_pct)
                        _, profit_target = get_grid_params(vol, grid_params)
                        tp_price = avg_entry * (1 + profit_target / 100 + maker_fee)
                        if high >= tp_price:
                            proceeds = total_qty * tp_price
                            sell_fee = proceeds * maker_fee
                            grid_total_fees += sell_fee
                            profit = proceeds - total_cost - sell_fee
                            cash += total_cost + profit
                            for l in grid_active_cycle["levels"]:
                                if l["status"] == "open":
                                    cash += l["capital"]
                            trade_num += 1
                            all_trades.append({
                                "trade_num": trade_num, "strategy": "dca_grid",
                                "exit_date": str(day["date"]),
                                "pnl_usd": profit,
                                "pnl_pct": (profit / total_cost * 100) if total_cost > 0 else 0,
                                "exit_reason": "batch_tp",
                            })
                            grid_cycles_completed.append(grid_active_cycle)
                            grid_active_cycle = None

                # FIFO TPs
                if filled and grid_active_cycle and grid_active_cycle["mode"] == "adaptive_fifo":
                    vol = get_volatility_regime(atr_pct)
                    _, profit_target = get_grid_params(vol, grid_params)
                    for lvl in grid_active_cycle["levels"]:
                        if lvl["status"] != "filled":
                            continue
                        tp = lvl["price"] * (1 + profit_target / 100 + maker_fee)
                        if high >= tp:
                            proceeds = lvl["quantity"] * tp
                            sell_fee = proceeds * maker_fee
                            grid_total_fees += sell_fee
                            profit = proceeds - lvl["capital"] - sell_fee
                            cash += lvl["capital"] + profit
                            lvl["status"] = "sold"
                            lvl["profit"] = profit
                            trade_num += 1
                            all_trades.append({
                                "trade_num": trade_num, "strategy": "dca_grid",
                                "exit_date": str(day["date"]),
                                "pnl_usd": profit,
                                "pnl_pct": (profit / lvl["capital"] * 100) if lvl["capital"] > 0 else 0,
                                "exit_reason": "fifo_tp",
                            })

                    filled_or_sold = [l for l in grid_active_cycle["levels"]
                                      if l["status"] in ("filled", "sold")]
                    if filled_or_sold and all(l["status"] == "sold" for l in filled_or_sold):
                        for l in grid_active_cycle["levels"]:
                            if l["status"] == "open":
                                cash += l["capital"]
                        grid_cycles_completed.append(grid_active_cycle)
                        grid_active_cycle = None

                # Stop-loss
                if grid_active_cycle and grid_active_cycle.get("stop_loss"):
                    if low <= grid_active_cycle["stop_loss"]:
                        filled = [l for l in grid_active_cycle["levels"] if l["status"] == "filled"]
                        total_cost = sum(l["capital"] for l in filled)
                        total_qty = sum(l["quantity"] for l in filled)
                        if total_qty > 0:
                            proceeds = total_qty * grid_active_cycle["stop_loss"]
                            sell_fee = proceeds * maker_fee
                            grid_total_fees += sell_fee
                            loss = proceeds - total_cost - sell_fee
                            cash += total_cost + loss
                            trade_num += 1
                            all_trades.append({
                                "trade_num": trade_num, "strategy": "dca_grid",
                                "exit_date": str(day["date"]),
                                "pnl_usd": loss, "pnl_pct": (loss / total_cost * 100) if total_cost > 0 else 0,
                                "exit_reason": "stop_loss",
                            })
                        for l in grid_active_cycle["levels"]:
                            if l["status"] == "open":
                                cash += l["capital"]
                        grid_cycles_completed.append(grid_active_cycle)
                        grid_active_cycle = None

                # Expiry
                if grid_active_cycle and grid_active_cycle.get("open_day_idx") is not None:
                    days_open = i - grid_active_cycle["open_day_idx"]
                    if days_open >= grid_max_cycle_hours / 24:
                        for l in grid_active_cycle["levels"]:
                            if l["status"] == "open":
                                cash += l["capital"]
                        grid_active_cycle["status"] = "expired_pending"
                        grid_expired_pending.append(grid_active_cycle)
                        grid_active_cycle = None

            # ── Check expired_pending TPs ──
            for exp in list(grid_expired_pending):
                for lvl in exp["levels"]:
                    if lvl["status"] == "filled":
                        vol = get_volatility_regime(atr_pct)
                        _, pt = get_grid_params(vol, grid_params)
                        tp = lvl["price"] * (1 + pt / 100 + maker_fee)
                        if high >= tp:
                            proceeds = lvl["quantity"] * tp
                            sell_fee = proceeds * maker_fee
                            grid_total_fees += sell_fee
                            profit = proceeds - lvl["capital"] - sell_fee
                            cash += lvl["capital"] + profit
                            lvl["status"] = "sold"
                            lvl["profit"] = profit
                            trade_num += 1
                            all_trades.append({
                                "trade_num": trade_num, "strategy": "dca_grid",
                                "exit_date": str(day["date"]),
                                "pnl_usd": profit,
                                "pnl_pct": (profit / lvl["capital"] * 100) if lvl["capital"] > 0 else 0,
                                "exit_reason": "expired_tp",
                            })
                remaining = [l for l in exp["levels"] if l["status"] == "filled"]
                if not remaining:
                    grid_expired_pending.remove(exp)
                    grid_cycles_completed.append(exp)

            # ── Open new grid cycle ──
            if not grid_active_cycle and not grid_paused:
                max_expired = grid_exit_params.get("max_expired_pending_per_asset", 2)
                can_open, _, is_defensive = should_open_cycle(
                    regime, rsi, atr_pct, False, len(grid_expired_pending), grid_params
                )
                if can_open:
                    cycle_capital = cash * grid_capital_pct
                    if cycle_capital >= 5:
                        cash -= cycle_capital
                        from decimal import Decimal as D
                        levels, stop, profit_target = compute_grid_levels(
                            D(str(close)), D(str(atr)), D(str(cycle_capital)),
                            grid_params, D(str(maker_fee)),
                        )
                        if levels:
                            mode = select_grid_mode(regime, grid_params)
                            grid_active_cycle = {
                                "mode": mode, "status": "active",
                                "open_day_idx": i, "stop_loss": float(stop),
                                "levels": [
                                    {"level": l.level, "price": float(l.price),
                                     "capital": float(l.capital), "quantity": float(l.quantity),
                                     "status": "open"}
                                    for l in levels
                                ],
                            }
                        else:
                            cash += cycle_capital

        # ═══════════════════════════════════════════════════════════
        # TREND MODE (RS >= 65)
        # ═══════════════════════════════════════════════════════════
        elif current_mode == "trend":
            if is_pyramid:
                # Update highest for open lots
                for lot in py_lots.values():
                    if lot.is_open:
                        lot.highest_since_entry = max(lot.highest_since_entry, high)

                # Exit checks (LIFO)
                hard_stop_pct = trend_params.get("exit", {}).get("hard_stop_pct", 5.0)
                hard_stop = False
                if py_base_entry > 0:
                    drop = (py_base_entry - close) / py_base_entry * 100
                    if drop >= hard_stop_pct:
                        hard_stop = True

                for label in ["D", "C", "B", "A"]:
                    lot = py_lots[label]
                    if not lot.is_open:
                        continue
                    exit_sig = None
                    if hard_stop:
                        exit_sig = True
                        reason = "hard_stop"
                    else:
                        sig = trend_strategy.should_exit_lot(lot, close, indicators)
                        if sig:
                            exit_sig = True
                            reason = (sig.reasons[0] if sig.reasons else f"Lot {label}")[:32]

                    if exit_sig:
                        fill = close * (1 - slip)
                        proceeds = lot.quantity * fill
                        fees = proceeds * taker_fee
                        cost = lot.cost_basis
                        pnl = proceeds - cost - fees
                        cash += proceeds - fees
                        trade_num += 1
                        all_trades.append({
                            "trade_num": trade_num, "strategy": "pyramid_trend",
                            "lot": label, "entry_date": lot.entry_date,
                            "exit_date": str(day["date"]),
                            "entry_price": lot.entry_price, "exit_price": fill,
                            "pnl_usd": pnl,
                            "pnl_pct": (pnl / cost * 100) if cost > 0 else 0,
                            "exit_reason": reason,
                        })
                        lot.is_open = False
                        lot.quantity = 0.0
                        lot.entry_price = 0.0

                any_open = any(l.is_open for l in py_lots.values())
                if not any_open and py_in_position:
                    py_in_position = False
                    py_base_entry = 0.0
                    py_cooldown = trend_params.get("pyramid", {}).get("cooldown_days", 5)

                # Pyramid: add lots
                if py_lots["A"].is_open and py_base_entry > 0:
                    for label in ["B", "C", "D"]:
                        lot = py_lots[label]
                        if lot.is_open:
                            continue
                        if trend_strategy.should_pyramid(label, py_base_entry, close):
                            alloc = lot.allocation_pct / 100
                            capital_base = (cash + sum(l.quantity * close for l in py_lots.values() if l.is_open)) if compound else initial_capital
                            amt = capital_base * trend_total_alloc_pct * alloc
                            if amt > cash:
                                amt = cash * 0.95
                            fill = open_price * (1 + slip)
                            qty = amt / fill
                            fees = amt * taker_fee
                            if amt > fees + 1:
                                cash -= amt + fees
                                lot.is_open = True
                                lot.entry_price = fill
                                lot.quantity = qty
                                lot.highest_since_entry = fill
                                lot.entry_date = str(days[i + 1]["date"] if i + 1 < len(days) else day["date"])

                # Entry: Lot A
                if not any_open and py_cooldown <= 0:
                    signal = trend_strategy.evaluate_signal(indicators)
                    if signal.has_signal and signal.side == "buy":
                        alloc = py_lots["A"].allocation_pct / 100
                        amt = initial_capital * trend_total_alloc_pct * alloc
                        if amt > cash:
                            amt = cash * 0.95
                        fill = open_price * (1 + slip)
                        qty = amt / fill
                        fees = amt * taker_fee
                        if amt > fees + 1:
                            cash -= amt + fees
                            py_lots["A"].is_open = True
                            py_lots["A"].entry_price = fill
                            py_lots["A"].quantity = qty
                            py_lots["A"].highest_since_entry = fill
                            py_lots["A"].entry_date = str(days[i + 1]["date"] if i + 1 < len(days) else day["date"])
                            py_base_entry = fill
                            py_in_position = True

                if py_cooldown > 0:
                    py_cooldown -= 1

            else:
                # Standard trend follow
                if tf_position_qty > 0:
                    tf_highest = max(tf_highest, high)
                    indicators["highest_since_entry"] = tf_highest
                    exit_sig = trend_strategy.should_exit(tf_entry_price, close, indicators)
                    if exit_sig and getattr(exit_sig, "has_signal", False):
                        fill = close * (1 - slip)
                        proceeds = tf_position_qty * fill
                        fees = proceeds * taker_fee
                        cost = tf_position_qty * tf_entry_price
                        pnl = proceeds - cost - fees
                        cash += proceeds - fees
                        trade_num += 1
                        all_trades.append({
                            "trade_num": trade_num, "strategy": "trend_follow",
                            "entry_price": tf_entry_price, "exit_price": fill,
                            "exit_date": str(day["date"]),
                            "pnl_usd": pnl,
                            "pnl_pct": (pnl / cost * 100) if cost > 0 else 0,
                            "exit_reason": (exit_sig.reasons[0] if exit_sig.reasons else "signal")[:32],
                        })
                        tf_position_qty = 0.0
                        tf_entry_price = 0.0
                        tf_highest = 0.0

                if tf_position_qty == 0:
                    signal = trend_strategy.evaluate_signal(indicators)
                    if signal.has_signal and signal.side == "buy":
                        cap_pct = trend_strategy.position.get("capital_per_trade_pct", 15) / 100
                        amt = cash * cap_pct
                        fill = open_price * (1 + slip)
                        qty = amt / fill
                        fees = amt * taker_fee
                        if amt > fees + 1:
                            cash -= amt + fees
                            tf_position_qty = qty
                            tf_entry_price = fill
                            tf_highest = fill

        # ═══════════════════════════════════════════════════════════
        # EQUITY TRACKING
        # ═══════════════════════════════════════════════════════════
        # Grid positions value (filled levels at current price)
        grid_value = 0.0
        if grid_active_cycle:
            for lvl in grid_active_cycle["levels"]:
                if lvl["status"] == "filled":
                    grid_value += lvl["quantity"] * close
        for exp in grid_expired_pending:
            for lvl in exp["levels"]:
                if lvl["status"] == "filled":
                    grid_value += lvl["quantity"] * close

        # Trend positions value
        trend_value = 0.0
        if grid_only:
            pass
        elif is_pyramid:
            trend_value = sum(l.quantity * close for l in py_lots.values() if l.is_open)
        else:
            trend_value = tf_position_qty * close

        portfolio_value = cash + grid_value + trend_value
        hodl_value = initial_capital * (close / first_close) if first_close > 0 else initial_capital

        if portfolio_value > peak_value:
            peak_value = portfolio_value
            dd_start = None
        drawdown = (portfolio_value - peak_value) / peak_value * 100 if peak_value > 0 else 0
        if drawdown < max_drawdown:
            max_drawdown = drawdown
            if dd_start is None:
                dd_start = i
            max_dd_duration = max(max_dd_duration, i - dd_start)

        equity_curve.append({
            "date": str(day["date"]),
            "portfolio": round(portfolio_value, 2),
            "cash": round(cash, 2),
            "grid": round(grid_value, 2),
            "trend": round(trend_value, 2),
            "hodl": round(hodl_value, 2),
            "mode": current_mode,
            "regime": round(regime, 1),
        })

    # ── Close remaining positions ──
    # Grid: return unfilled capital, mark filled at current price
    if grid_active_cycle:
        for lvl in grid_active_cycle["levels"]:
            if lvl["status"] == "open":
                cash += lvl["capital"]
            elif lvl["status"] == "filled":
                proceeds = lvl["quantity"] * last_close
                fee = proceeds * maker_fee
                cash += proceeds - fee
                trade_num += 1
                all_trades.append({
                    "trade_num": trade_num, "strategy": "dca_grid",
                    "exit_date": str(days[-1]["date"]),
                    "pnl_usd": proceeds - lvl["capital"] - fee,
                    "pnl_pct": ((proceeds - lvl["capital"] - fee) / lvl["capital"] * 100) if lvl["capital"] > 0 else 0,
                    "exit_reason": "end_of_period",
                })
    for exp in grid_expired_pending:
        for lvl in exp["levels"]:
            if lvl["status"] == "filled":
                proceeds = lvl["quantity"] * last_close
                fee = proceeds * maker_fee
                cash += proceeds - fee

    # Trend: close positions
    if is_pyramid:
        for label in ["D", "C", "B", "A"]:
            lot = py_lots[label]
            if not lot.is_open:
                continue
            fill = last_close * (1 - slip)
            proceeds = lot.quantity * fill
            fees = proceeds * taker_fee
            cost = lot.cost_basis
            pnl = proceeds - cost - fees
            cash += proceeds - fees
            trade_num += 1
            all_trades.append({
                "trade_num": trade_num, "strategy": "pyramid_trend",
                "lot": label, "exit_date": str(days[-1]["date"]),
                "entry_price": lot.entry_price, "exit_price": fill,
                "pnl_usd": pnl,
                "pnl_pct": (pnl / cost * 100) if cost > 0 else 0,
                "exit_reason": "end_of_period",
            })
    elif tf_position_qty > 0:
        fill = last_close * (1 - slip)
        proceeds = tf_position_qty * fill
        fees = proceeds * taker_fee
        cost = tf_position_qty * tf_entry_price
        pnl = proceeds - cost - fees
        cash += proceeds - fees
        trade_num += 1
        all_trades.append({
            "trade_num": trade_num, "strategy": "trend_follow",
            "exit_date": str(days[-1]["date"]),
            "entry_price": tf_entry_price, "exit_price": fill,
            "pnl_usd": pnl,
            "pnl_pct": (pnl / cost * 100) if cost > 0 else 0,
            "exit_reason": "end_of_period",
        })

    # ── Compute metrics ──
    final_value = cash
    total_return = final_value - initial_capital
    total_return_pct = total_return / initial_capital * 100
    hodl_return_pct = ((last_close - first_close) / first_close * 100) if first_close > 0 else 0

    sell_trades = [t for t in all_trades if t.get("pnl_usd") is not None]
    wins = [t for t in sell_trades if t["pnl_usd"] > 0]
    losses = [t for t in sell_trades if t["pnl_usd"] <= 0]

    grid_trades = [t for t in sell_trades if t["strategy"] == "dca_grid"]
    trend_trades = [t for t in sell_trades if t["strategy"] in ("pyramid_trend", "trend_follow")]

    # Days in each mode
    grid_days = sum(1 for e in equity_curve if e["mode"] == "grid")
    trend_days = sum(1 for e in equity_curve if e["mode"] == "trend")

    run_duration = int((time.monotonic() - start_time) * 1000)

    return {
        "asset": asset_symbol,
        "trend_strategy": trend_type,
        "period": f"{days[0]['date']} to {days[-1]['date']} ({len(days)} days)",
        "initial_capital": initial_capital,
        "performance": {
            "total_return_pct": round(total_return_pct, 2),
            "total_return_usd": round(total_return, 2),
            "hodl_return_pct": round(hodl_return_pct, 2),
            "alpha_pct": round(total_return_pct - hodl_return_pct, 2),
            "max_drawdown_pct": round(max_drawdown, 2),
            "max_drawdown_duration_days": max_dd_duration,
        },
        "trades": {
            "total": len(sell_trades),
            "winning": len(wins),
            "losing": len(losses),
            "win_rate": round(len(wins) / len(sell_trades), 2) if sell_trades else 0,
            "avg_win_pct": round(sum(t["pnl_pct"] for t in wins) / len(wins), 2) if wins else 0,
            "avg_loss_pct": round(sum(t["pnl_pct"] for t in losses) / len(losses), 2) if losses else 0,
        },
        "breakdown": {
            "grid_trades": len(grid_trades),
            "grid_pnl": round(sum(t["pnl_usd"] for t in grid_trades), 2),
            "trend_trades": len(trend_trades),
            "trend_pnl": round(sum(t["pnl_usd"] for t in trend_trades), 2),
            "grid_days": grid_days,
            "trend_days": trend_days,
        },
        "regime_transitions": len(regime_log),
        "run_duration_ms": run_duration,
    }


def cmd_run(args):
    s = schema()
    with sync_connect() as conn:
        # Load asset
        cur = conn.execute(f"SELECT id FROM {s}.assets WHERE symbol = %s", (args.asset.upper(),))
        asset = cur.fetchone()
        if not asset:
            error(f"Asset '{args.asset}' not found")
        asset_id = asset["id"]
        asset_symbol = args.asset.upper()

        # Load grid strategy params
        cur = conn.execute(
            f"SELECT params FROM {s}.strategies WHERE name = %s AND is_current = true",
            (f"{asset_symbol.lower()}_dca_grid",),
        )
        grid_row = cur.fetchone()
        if not grid_row:
            error(f"Grid strategy '{asset_symbol.lower()}_dca_grid' not found")
        grid_params = grid_row["params"] if isinstance(grid_row["params"], dict) else json.loads(grid_row["params"])

        # Load trend strategy params (None = grid-only)
        trend_type = TREND_STRATEGY_TYPE.get(asset_symbol, "trend_follow")
        trend_params = {}
        if trend_type is not None:
            trend_name = f"{asset_symbol.lower()}_{trend_type}"
            cur = conn.execute(
                f"SELECT params FROM {s}.strategies WHERE name = %s AND is_current = true",
                (trend_name,),
            )
            trend_row = cur.fetchone()
            if not trend_row:
                error(f"Trend strategy '{trend_name}' not found")
            trend_params = trend_row["params"] if isinstance(trend_row["params"], dict) else json.loads(trend_row["params"])

        # Load data
        days = _load_daily_data(conn, s, asset_id, args.date_from, args.date_to)

        result = _run_composite(
            conn, s, asset_symbol, asset_id,
            grid_params, trend_params, trend_type,
            days, args.capital,
            compound=args.compound,
        )

    output(result)


def main():
    parser = argparse.ArgumentParser(prog="python -m cli.backtest_composite")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("run")
    p.add_argument("--asset", required=True, help="Asset symbol (BTC, ETH, SOL, XRP)")
    p.add_argument("--from", dest="date_from", type=date.fromisoformat, required=True)
    p.add_argument("--to", dest="date_to", type=date.fromisoformat, required=True)
    p.add_argument("--capital", type=float, default=1000)
    p.add_argument("--compound", action="store_true", help="Use current equity as capital base (compound profits)")

    args = parser.parse_args()
    {"run": cmd_run}[args.command](args)


if __name__ == "__main__":
    main()
