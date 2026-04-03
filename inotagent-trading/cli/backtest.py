"""Backtesting CLI — replay strategies against historical data.

Uses the SAME strategy code as live signal scanner. No divergence.

Usage:
    python -m cli.backtest run --strategy cro_momentum --from 2025-01-01 --to 2026-03-31
    python -m cli.backtest sweep --strategy cro_momentum --from 2025-01-01 --to 2026-03-31 --sweep entry.rsi_buy_threshold=20,25,30
    python -m cli.backtest list --strategy cro_momentum
    python -m cli.backtest view --id 42
"""

from __future__ import annotations

import argparse
import copy
import json
import time
import uuid
from datetime import date, datetime
from decimal import Decimal

from cli import error, output
from core.db import schema, sync_connect
from guardrails import MAX_OPEN_POSITIONS, STOP_LOSS_REQUIRED
from strategies.momentum import get_strategy


def _run_backtest(
    conn, s: str, strategy_name: str, strategy_type: str, params: dict,
    asset_id: int, venue_id: int, date_from: date, date_to: date,
    initial_capital: Decimal, slippage_pct: Decimal,
    maker_fee: Decimal | None, taker_fee: Decimal | None,
    sweep_id: str | None = None, created_by: str = "cli",
) -> dict:
    """Execute a single backtest run. Returns result dict."""
    start_time = time.monotonic()

    strategy = get_strategy(strategy_type, params)

    # Load daily indicators for the period
    cur = conn.execute(
        f"""SELECT i.date, i.rsi_14, i.rsi_7, i.ema_9, i.ema_20, i.ema_50, i.ema_200,
                   i.sma_50, i.sma_200, i.macd, i.macd_signal, i.macd_hist,
                   i.atr_14, i.bb_upper, i.bb_lower, i.bb_width, i.adx_14,
                   i.obv, i.volume_sma_20, i.volume_ratio, i.regime_score,
                   d.open, d.high, d.low, d.close, d.volume
            FROM {s}.indicators_daily i
            JOIN {s}.ohlcv_daily d ON d.asset_id = i.asset_id AND d.date = i.date
            WHERE i.asset_id = %s AND i.date BETWEEN %s AND %s
            ORDER BY i.date""",
        (asset_id, date_from, date_to),
    )
    days = [dict(r) for r in cur.fetchall()]

    if len(days) < 15:
        return {"error": f"Insufficient data: {len(days)} days (need at least 15)"}

    # Load first day's OHLCV for HODL benchmark
    first_close = float(days[0]["close"])
    last_close = float(days[-1]["close"])

    # Simulation state
    cash = float(initial_capital)
    position_qty = 0.0
    entry_price = 0.0
    trades = []
    equity_curve = []
    peak_value = float(initial_capital)
    max_drawdown = 0.0
    max_dd_duration = 0
    dd_start = None
    trade_num = 0

    slip = float(slippage_pct) / 100
    fee_rate = float(taker_fee or Decimal("0.0025"))

    for i, day in enumerate(days):
        indicators = {k: float(v) if v is not None else None for k, v in day.items()
                      if k not in ("date", "open", "high", "low", "close", "volume")}
        close = float(day["close"])
        high = float(day["high"])
        low = float(day["low"])
        open_price = float(days[i + 1]["open"]) if i + 1 < len(days) else close

        # Check stop-loss/take-profit on open positions
        if position_qty > 0:
            exit_signal = strategy.should_exit(entry_price, close, indicators)

            # Also check intraday stop-loss via high/low
            sl_pct = strategy.exit.get("stop_loss_pct", 0)
            if sl_pct > 0:
                sl_price = entry_price * (1 - sl_pct / 100)
                if low <= sl_price:
                    exit_signal = exit_signal or type(exit_signal)  # prioritize
                    exit_signal = type('Signal', (), {
                        'side': 'sell', 'confidence': 1.0, 'has_signal': True,
                        'reasons': [f"Stop-loss hit intraday: low={low:.6f} <= {sl_price:.6f}"],
                        'failed_conditions': [], 'indicators': {},
                    })()

            if exit_signal and getattr(exit_signal, 'has_signal', False):
                # Sell
                fill_price = close * (1 - slip)
                proceeds = position_qty * fill_price
                fees = proceeds * fee_rate
                cost_basis = position_qty * entry_price
                pnl = proceeds - cost_basis - fees
                pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0

                cash += proceeds - fees
                trade_num += 1
                trades.append({
                    "trade_num": trade_num,
                    "entry_date": trades[-1]["entry_date"] if trades else str(day["date"]),
                    "entry_price": entry_price,
                    "exit_date": str(day["date"]),
                    "exit_price": fill_price,
                    "exit_reason": exit_signal.reasons[0] if exit_signal.reasons else "signal",
                    "side": "sell",
                    "quantity": position_qty,
                    "cost_basis_usd": cost_basis,
                    "proceeds_usd": proceeds,
                    "fees_usd": fees,
                    "pnl_usd": pnl,
                    "pnl_pct": pnl_pct,
                })
                position_qty = 0.0
                entry_price = 0.0

        # Evaluate entry signal (only if no position)
        if position_qty == 0:
            signal = strategy.evaluate_signal(indicators)
            if signal.has_signal and signal.side == "buy":
                # Buy at next day's open + slippage
                fill_price = open_price * (1 + slip)
                capital_pct = strategy.position.get("capital_per_trade_pct", 10) / 100
                trade_amount = cash * capital_pct
                quantity = trade_amount / fill_price
                fees = trade_amount * fee_rate

                if trade_amount > fees + 1:  # min viable trade
                    cash -= trade_amount + fees
                    position_qty = quantity
                    entry_price = fill_price

                    trade_num += 1
                    trades.append({
                        "trade_num": trade_num,
                        "entry_date": str(days[i + 1]["date"] if i + 1 < len(days) else day["date"]),
                        "entry_price": fill_price,
                        "entry_signal_confidence": signal.confidence,
                        "entry_reasons": signal.reasons,
                        "side": "buy",
                        "quantity": quantity,
                    })

        # Record equity
        portfolio_value = cash + position_qty * close
        hodl_value = float(initial_capital) * (close / first_close) if first_close > 0 else float(initial_capital)

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
            "portfolio_value_usd": round(portfolio_value, 2),
            "cash_usd": round(cash, 2),
            "positions_value_usd": round(position_qty * close, 2),
            "hodl_value_usd": round(hodl_value, 2),
            "drawdown_pct": round(drawdown, 4),
        })

    # Close any remaining position at last close
    if position_qty > 0:
        proceeds = position_qty * last_close * (1 - slip)
        fees = proceeds * fee_rate
        cost_basis = position_qty * entry_price
        pnl = proceeds - cost_basis - fees
        cash += proceeds - fees
        trade_num += 1
        trades.append({
            "trade_num": trade_num,
            "entry_date": trades[-1].get("entry_date", ""),
            "entry_price": entry_price,
            "exit_date": str(days[-1]["date"]),
            "exit_price": last_close,
            "exit_reason": "end_of_period",
            "side": "sell",
            "quantity": position_qty,
            "cost_basis_usd": cost_basis,
            "proceeds_usd": proceeds,
            "fees_usd": fees,
            "pnl_usd": pnl,
            "pnl_pct": (pnl / cost_basis * 100) if cost_basis > 0 else 0,
        })
        position_qty = 0.0

    # Compute metrics
    final_value = cash
    total_return = final_value - float(initial_capital)
    total_return_pct = total_return / float(initial_capital) * 100
    hodl_return_pct = ((last_close - first_close) / first_close * 100) if first_close > 0 else 0

    sell_trades = [t for t in trades if t.get("pnl_usd") is not None]
    wins = [t for t in sell_trades if t["pnl_usd"] > 0]
    losses = [t for t in sell_trades if t["pnl_usd"] <= 0]

    run_duration = int((time.monotonic() - start_time) * 1000)

    result = {
        "strategy_name": strategy_name,
        "strategy_type": strategy_type,
        "period": f"{date_from} to {date_to} ({len(days)} days)",
        "initial_capital": float(initial_capital),
        "performance": {
            "total_return_pct": round(total_return_pct, 4),
            "total_return_usd": round(total_return, 2),
            "hodl_return_pct": round(hodl_return_pct, 4),
            "alpha_pct": round(total_return_pct - hodl_return_pct, 4),
            "max_drawdown_pct": round(max_drawdown, 4),
            "max_drawdown_duration_days": max_dd_duration,
        },
        "trades": {
            "total": len(sell_trades),
            "winning": len(wins),
            "losing": len(losses),
            "win_rate": round(len(wins) / len(sell_trades), 4) if sell_trades else 0,
            "avg_win_pct": round(sum(t["pnl_pct"] for t in wins) / len(wins), 4) if wins else 0,
            "avg_loss_pct": round(sum(t["pnl_pct"] for t in losses) / len(losses), 4) if losses else 0,
        },
        "run_duration_ms": run_duration,
    }

    # Save to DB
    cur = conn.execute(
        f"""INSERT INTO {s}.backtest_runs
            (sweep_id, strategy_name, strategy_type, strategy_params, asset_id, venue_id,
             date_from, date_to, initial_capital_usd, slippage_pct, maker_fee, taker_fee,
             total_return_pct, total_return_usd, hodl_return_pct, alpha_pct,
             total_trades, winning_trades, losing_trades, win_rate,
             avg_win_pct, avg_loss_pct, max_drawdown_pct, max_drawdown_duration_days,
             run_duration_ms, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id""",
        (
            sweep_id, strategy_name, strategy_type, json.dumps(params), asset_id, venue_id,
            date_from, date_to, initial_capital, slippage_pct, maker_fee, taker_fee,
            Decimal(str(result["performance"]["total_return_pct"])),
            Decimal(str(result["performance"]["total_return_usd"])),
            Decimal(str(result["performance"]["hodl_return_pct"])),
            Decimal(str(result["performance"]["alpha_pct"])),
            result["trades"]["total"], result["trades"]["winning"], result["trades"]["losing"],
            Decimal(str(result["trades"]["win_rate"])),
            Decimal(str(result["trades"]["avg_win_pct"])),
            Decimal(str(result["trades"]["avg_loss_pct"])),
            Decimal(str(result["performance"]["max_drawdown_pct"])),
            result["performance"]["max_drawdown_duration_days"],
            run_duration, created_by,
        ),
    )
    run_id = cur.fetchone()["id"]
    result["run_id"] = run_id

    # Save trades
    for t in sell_trades:
        conn.execute(
            f"""INSERT INTO {s}.backtest_trades
                (run_id, trade_num, entry_date, entry_price, entry_signal_confidence, entry_reasons,
                 exit_date, exit_price, exit_reason, side, quantity,
                 cost_basis_usd, proceeds_usd, fees_usd, pnl_usd, pnl_pct)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                run_id, t["trade_num"], t.get("entry_date"), t.get("entry_price"),
                t.get("entry_signal_confidence"),
                json.dumps(t.get("entry_reasons")) if t.get("entry_reasons") else None,
                t.get("exit_date"), t.get("exit_price"), t.get("exit_reason"),
                "sell", t["quantity"],
                Decimal(str(t.get("cost_basis_usd", 0))),
                Decimal(str(t.get("proceeds_usd", 0))),
                Decimal(str(t.get("fees_usd", 0))),
                Decimal(str(t["pnl_usd"])),
                Decimal(str(t["pnl_pct"])),
            ),
        )

    # Save equity curve
    for e in equity_curve:
        conn.execute(
            f"""INSERT INTO {s}.backtest_equity
                (run_id, date, portfolio_value_usd, cash_usd, positions_value_usd,
                 hodl_value_usd, drawdown_pct)
                VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (run_id, e["date"], e["portfolio_value_usd"], e["cash_usd"],
             e["positions_value_usd"], e["hodl_value_usd"], e["drawdown_pct"]),
        )

    conn.commit()
    return result


def cmd_run(args):
    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(
            f"""SELECT s.*, a.id AS resolved_asset_id, v.id AS resolved_venue_id
                FROM {s}.strategies s
                LEFT JOIN trading_platform.assets a ON a.id = s.asset_id
                LEFT JOIN trading_platform.venues v ON v.id = s.venue_id
                WHERE s.name = %s AND s.is_current = true""",
            (args.strategy,),
        )
        strat = cur.fetchone()
        if not strat:
            error(f"Strategy '{args.strategy}' not found")
        strat = dict(strat)

        params = strat["params"] if isinstance(strat["params"], dict) else json.loads(strat["params"])

        # Apply overrides
        if args.override:
            for o in args.override:
                key, _, value = o.partition("=")
                parts = key.split(".")
                target = params
                for p in parts[:-1]:
                    target = target.setdefault(p, {})
                try:
                    target[parts[-1]] = json.loads(value)
                except json.JSONDecodeError:
                    target[parts[-1]] = value

        result = _run_backtest(
            conn, s, strat["name"], strat["type"], params,
            strat["resolved_asset_id"], strat["resolved_venue_id"],
            args.date_from, args.date_to,
            Decimal(str(args.capital)), Decimal(str(args.slippage)),
            None, None,
        )

    output(result)


def cmd_sweep(args):
    s = schema()
    sweep_id = str(uuid.uuid4())

    # Parse sweep params
    sweep_params = {}
    for sw in args.sweep:
        key, _, values = sw.partition("=")
        sweep_params[key] = [json.loads(v) if v.replace(".", "").isdigit() else v for v in values.split(",")]

    # Generate all combinations
    import itertools
    keys = list(sweep_params.keys())
    combos = list(itertools.product(*[sweep_params[k] for k in keys]))

    with sync_connect() as conn:
        cur = conn.execute(
            f"""SELECT s.*, a.id AS resolved_asset_id, v.id AS resolved_venue_id
                FROM {s}.strategies s
                LEFT JOIN trading_platform.assets a ON a.id = s.asset_id
                LEFT JOIN trading_platform.venues v ON v.id = s.venue_id
                WHERE s.name = %s AND s.is_current = true""",
            (args.strategy,),
        )
        strat = cur.fetchone()
        if not strat:
            error(f"Strategy '{args.strategy}' not found")
        strat = dict(strat)
        base_params = strat["params"] if isinstance(strat["params"], dict) else json.loads(strat["params"])

        results = []
        for combo in combos:
            params = copy.deepcopy(base_params)
            combo_desc = {}
            for i, key in enumerate(keys):
                parts = key.split(".")
                target = params
                for p in parts[:-1]:
                    target = target.setdefault(p, {})
                target[parts[-1]] = combo[i]
                combo_desc[key] = combo[i]

            result = _run_backtest(
                conn, s, strat["name"], strat["type"], params,
                strat["resolved_asset_id"], strat["resolved_venue_id"],
                args.date_from, args.date_to,
                Decimal(str(args.capital)), Decimal(str(args.slippage)),
                None, None, sweep_id=sweep_id,
            )
            result["params_override"] = combo_desc
            results.append(result)

    # Sort by return
    results.sort(key=lambda r: r.get("performance", {}).get("total_return_pct", 0), reverse=True)
    output({"sweep_id": sweep_id, "combinations": len(results), "results": results})


def cmd_list(args):
    s = schema()
    with sync_connect() as conn:
        conditions = ["true"]
        params = []
        if args.strategy:
            conditions.append("strategy_name = %s")
            params.append(args.strategy)

        cur = conn.execute(
            f"""SELECT id, sweep_id, strategy_name, date_from, date_to,
                       total_return_pct, hodl_return_pct, alpha_pct,
                       total_trades, win_rate, max_drawdown_pct, sharpe_ratio,
                       created_at
                FROM {s}.backtest_runs
                WHERE {' AND '.join(conditions)}
                ORDER BY created_at DESC LIMIT 20""",
            params,
        )
        rows = cur.fetchall()
    output([dict(r) for r in rows])


def cmd_view(args):
    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(f"SELECT * FROM {s}.backtest_runs WHERE id = %s", (args.id,))
        run = cur.fetchone()
        if not run:
            error(f"Backtest run {args.id} not found")

        cur = conn.execute(
            f"SELECT * FROM {s}.backtest_trades WHERE run_id = %s ORDER BY trade_num", (args.id,)
        )
        trades = cur.fetchall()

    output({"run": dict(run), "trades": [dict(t) for t in trades]})


def main():
    parser = argparse.ArgumentParser(prog="python -m cli.backtest", description="Backtesting CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("run")
    p.add_argument("--strategy", required=True)
    p.add_argument("--from", dest="date_from", type=date.fromisoformat, required=True)
    p.add_argument("--to", dest="date_to", type=date.fromisoformat, required=True)
    p.add_argument("--capital", type=float, default=1000)
    p.add_argument("--slippage", type=float, default=0.10)
    p.add_argument("--override", action="append", help="key=value param override")

    p = sub.add_parser("sweep")
    p.add_argument("--strategy", required=True)
    p.add_argument("--from", dest="date_from", type=date.fromisoformat, required=True)
    p.add_argument("--to", dest="date_to", type=date.fromisoformat, required=True)
    p.add_argument("--capital", type=float, default=1000)
    p.add_argument("--slippage", type=float, default=0.10)
    p.add_argument("--sweep", action="append", required=True, help="key=v1,v2,v3")

    p = sub.add_parser("list")
    p.add_argument("--strategy", default=None)

    p = sub.add_parser("view")
    p.add_argument("--id", type=int, required=True)

    args = parser.parse_args()
    commands = {"run": cmd_run, "sweep": cmd_sweep, "list": cmd_list, "view": cmd_view}
    commands[args.command](args)


if __name__ == "__main__":
    main()
