"""Trade CLI — order management with guardrail validation.

Usage:
    python -m cli.trade <command> [args]
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal

from cli import error, output
from core.db import schema, sync_connect
from guardrails import load_guardrail_config, validate_order


def _resolve_ids(conn, s: str, symbol: str, venue: str):
    """Resolve asset_id, venue_id, account_id, trading_pair_id from symbol + venue."""
    cur = conn.execute(f"SELECT id FROM {s}.assets WHERE symbol = %s", (symbol.upper(),))
    asset = cur.fetchone()
    if not asset:
        error(f"Asset '{symbol}' not found")

    cur = conn.execute(f"SELECT id FROM {s}.venues WHERE code = %s", (venue,))
    venue_row = cur.fetchone()
    if not venue_row:
        error(f"Venue '{venue}' not found")

    cur = conn.execute(
        f"""SELECT id FROM {s}.accounts
            WHERE venue_id = %s AND is_default = true AND deleted_at IS NULL""",
        (venue_row["id"],),
    )
    account = cur.fetchone()
    if not account:
        error(f"No default account for venue '{venue}'")

    cur = conn.execute(
        f"""SELECT id FROM {s}.trading_pairs
            WHERE venue_id = %s AND base_asset_id = %s AND is_current = true""",
        (venue_row["id"], asset["id"]),
    )
    pair = cur.fetchone()

    return asset["id"], venue_row["id"], account["id"], pair["id"] if pair else None


def _get_portfolio_state(conn, s: str) -> tuple[Decimal, int, Decimal]:
    """Get portfolio value, open position count, daily P&L pct."""
    cur = conn.execute(
        f"SELECT COALESCE(SUM(balance_usd), 0) AS total FROM {s}.balances"
    )
    portfolio_value = cur.fetchone()["total"] or Decimal("1000")

    cur = conn.execute(
        f"""SELECT COUNT(DISTINCT asset_id) FROM {s}.orders
            WHERE status IN ('open', 'filled', 'partial') AND side = 'buy' AND paper = false"""
    )
    open_positions = cur.fetchone()["count"]

    cur = conn.execute(
        f"""SELECT COALESCE(SUM(pnl_usd), 0) AS daily
            FROM {s}.pnl_realized WHERE created_at::date = CURRENT_DATE"""
    )
    daily_pnl = cur.fetchone()["daily"]
    daily_pnl_pct = daily_pnl / portfolio_value if portfolio_value > 0 else Decimal("0")

    return portfolio_value, open_positions, daily_pnl_pct


def _get_allowed_pairs(conn, s: str) -> list[str]:
    """Load active trading pair symbols from DB."""
    cur = conn.execute(
        f"SELECT pair_symbol FROM {s}.trading_pairs WHERE is_active = true AND is_current = true"
    )
    return [r["pair_symbol"] for r in cur.fetchall()]


def cmd_buy(args):
    s = schema()
    with sync_connect() as conn:
        asset_id, venue_id, account_id, pair_id = _resolve_ids(conn, s, args.symbol, args.venue)
        portfolio_value, open_positions, daily_pnl_pct = _get_portfolio_state(conn, s)

        # Guardrail check
        stop_loss_pct = None
        if args.stop_loss and args.price:
            stop_loss_pct = abs(args.price - args.stop_loss) / args.price

        # Resolve pair symbol from trading_pairs table
        cur = conn.execute(
            f"""SELECT tp.pair_symbol FROM {s}.trading_pairs tp
                WHERE tp.base_asset_id = %s AND tp.venue_id = %s AND tp.is_current = true""",
            (asset_id, venue_id),
        )
        pair_row = cur.fetchone()
        pair_symbol = pair_row["pair_symbol"] if pair_row else f"{args.symbol.upper()}/USDT"

        allowed_pairs = _get_allowed_pairs(conn, s)
        guardrail_config = load_guardrail_config(conn, s)
        check = validate_order(
            pair_symbol=pair_symbol,
            side="buy",
            amount_usd=args.amount,
            portfolio_value_usd=portfolio_value,
            open_position_count=open_positions,
            daily_pnl_pct=daily_pnl_pct,
            stop_loss_pct=stop_loss_pct,
            allowed_pairs=allowed_pairs,
            config=guardrail_config,
        )

        if not check.passed:
            error(f"Guardrail violation: {'; '.join(check.violations)}")

        if check.needs_human_approval:
            output({"status": "needs_approval", "violations": [], "message": "Trade exceeds human approval threshold"})
            return

        # Resolve strategy
        strategy_id = None
        strategy_version = None
        if args.strategy:
            cur = conn.execute(
                f"SELECT id, version FROM {s}.strategies WHERE name = %s AND is_current = true",
                (args.strategy,),
            )
            strat = cur.fetchone()
            if strat:
                strategy_id = strat["id"]
                strategy_version = strat["version"]

        # Calculate quantity from amount
        quantity = args.amount / args.price if args.price else args.amount

        # Determine paper mode
        paper = True
        if strategy_id:
            cur = conn.execute(f"SELECT paper_mode FROM {s}.strategies WHERE id = %s", (strategy_id,))
            strat_row = cur.fetchone()
            if strat_row:
                paper = strat_row["paper_mode"]

        # Insert order
        cur = conn.execute(
            f"""INSERT INTO {s}.orders
                (strategy_id, asset_id, venue_id, account_id, trading_pair_id,
                 side, type, quantity, price, stop_loss, take_profit,
                 paper, strategy_version, guardrails_snapshot, rationale, created_by)
                VALUES (%s, %s, %s, %s, %s, 'buy', %s, %s, %s, %s, %s, %s, %s, %s, %s, 'robin')
                RETURNING id""",
            (strategy_id, asset_id, venue_id, account_id, pair_id,
             "limit" if args.price else "market", quantity, args.price,
             args.stop_loss, args.take_profit,
             paper, strategy_version, json.dumps(check.snapshot), args.rationale),
        )
        order = cur.fetchone()

        # Insert order event
        conn.execute(
            f"""INSERT INTO {s}.order_events (order_id, to_status, reason, changed_by)
                VALUES (%s, 'open', 'order placed', 'robin')""",
            (order["id"],),
        )

        # If paper mode, simulate instant fill
        if paper:
            from core.exchange import PaperExchange
            pe = PaperExchange.__new__(PaperExchange)
            pe._order_counter = order["id"]
            pe._live = None  # Not needed for fee calc

            fee_rate = float(PaperExchange.DEFAULT_TAKER_FEE)
            fill_price = float(args.price or 0)
            fee_cost = float(quantity) * fill_price * fee_rate

            conn.execute(
                f"UPDATE {s}.orders SET status = 'filled', filled_at = NOW(), exchange_order_id = %s WHERE id = %s",
                (f"PAPER-{order['id']}", order["id"]),
            )
            conn.execute(
                f"""INSERT INTO {s}.executions (order_id, quantity, price, fee, fee_currency)
                    VALUES (%s, %s, %s, %s, 'USD')""",
                (order["id"], quantity, args.price, Decimal(str(fee_cost))),
            )
            conn.execute(
                f"""INSERT INTO {s}.order_events (order_id, from_status, to_status, reason, changed_by)
                    VALUES (%s, 'open', 'filled', 'paper instant fill', 'system')""",
                (order["id"],),
            )

            # Create cost basis lot
            conn.execute(
                f"""INSERT INTO {s}.cost_basis
                    (account_id, asset_id, strategy_id, buy_order_id,
                     quantity_original, quantity_remaining, cost_per_unit_usd, acquired_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())""",
                (account_id, asset_id, strategy_id, order["id"],
                 quantity, quantity, args.price),
            )

        conn.commit()

    output({
        "status": "ok",
        "order_id": order["id"],
        "side": "buy",
        "symbol": args.symbol.upper(),
        "quantity": float(quantity),
        "price": float(args.price) if args.price else None,
        "paper": paper,
    })


def cmd_sell(args):
    s = schema()
    with sync_connect() as conn:
        asset_id, venue_id, account_id, pair_id = _resolve_ids(conn, s, args.symbol, args.venue)

        strategy_id = None
        if args.strategy:
            cur = conn.execute(
                f"SELECT id FROM {s}.strategies WHERE name = %s AND is_current = true", (args.strategy,)
            )
            strat = cur.fetchone()
            if strat:
                strategy_id = strat["id"]

        paper = not getattr(args, "live", False)
        if strategy_id and not getattr(args, "live", False):
            cur = conn.execute(f"SELECT paper_mode FROM {s}.strategies WHERE id = %s", (strategy_id,))
            strat_row = cur.fetchone()
            if strat_row:
                paper = strat_row["paper_mode"]

        cur = conn.execute(
            f"""INSERT INTO {s}.orders
                (strategy_id, asset_id, venue_id, account_id, trading_pair_id,
                 side, type, quantity, price, paper, rationale, created_by)
                VALUES (%s, %s, %s, %s, %s, 'sell', %s, %s, %s, %s, %s, 'robin')
                RETURNING id""",
            (strategy_id, asset_id, venue_id, account_id, pair_id,
             "limit" if args.price else "market", args.quantity, args.price, paper, args.rationale),
        )
        order = cur.fetchone()

        conn.execute(
            f"""INSERT INTO {s}.order_events (order_id, to_status, reason, changed_by)
                VALUES (%s, 'open', 'order placed', 'robin')""",
            (order["id"],),
        )

        # Live order: call exchange API
        if not paper:
            from core.exchange import CcxtExchange
            ex = CcxtExchange()
            account_row = conn.execute(
                f"SELECT address FROM {s}.accounts WHERE id = %s", (account_id,)
            ).fetchone()
            account_addr = account_row["address"] if account_row else None

            ex_order = ex.create_order(
                f"{args.symbol.upper()}/USDT",
                "limit" if args.price else "market",
                "sell", float(args.quantity), float(args.price) if args.price else None,
                account_address=account_addr,
            )
            conn.execute(
                f"UPDATE {s}.orders SET exchange_order_id = %s WHERE id = %s",
                (str(ex_order["id"]), order["id"]),
            )
            conn.commit()
            output({
                "status": "ok",
                "order_id": order["id"],
                "exchange_order_id": ex_order["id"],
                "side": "sell",
                "symbol": args.symbol.upper(),
                "quantity": float(args.quantity),
                "price": float(args.price) if args.price else None,
                "paper": False,
            })
            return

        # Paper instant fill + FIFO cost basis consumption
        if paper:
            fill_price = args.price or Decimal("0")
            from core.exchange import PaperExchange
            fee_rate = float(PaperExchange.DEFAULT_TAKER_FEE)
            fee_cost = float(args.quantity) * float(fill_price) * fee_rate

            conn.execute(
                f"UPDATE {s}.orders SET status = 'filled', filled_at = NOW(), exchange_order_id = %s WHERE id = %s",
                (f"PAPER-{order['id']}", order["id"]),
            )
            exec_cur = conn.execute(
                f"""INSERT INTO {s}.executions (order_id, quantity, price, fee, fee_currency)
                    VALUES (%s, %s, %s, %s, 'USD') RETURNING id""",
                (order["id"], args.quantity, fill_price, Decimal(str(fee_cost))),
            )
            execution = exec_cur.fetchone()

            # Consume FIFO cost basis lots
            remaining_to_sell = args.quantity
            total_cost = Decimal("0")

            cur = conn.execute(
                f"""SELECT id, quantity_remaining, cost_per_unit_usd
                    FROM {s}.cost_basis
                    WHERE account_id = %s AND asset_id = %s AND is_closed = false
                    ORDER BY acquired_at ASC""",
                (account_id, asset_id),
            )
            lots = cur.fetchall()

            for lot in lots:
                if remaining_to_sell <= 0:
                    break
                consume = min(remaining_to_sell, lot["quantity_remaining"])
                total_cost += consume * lot["cost_per_unit_usd"]
                new_remaining = lot["quantity_remaining"] - consume
                is_closed = new_remaining <= 0

                conn.execute(
                    f"""UPDATE {s}.cost_basis
                        SET quantity_remaining = %s, is_closed = %s,
                            closed_at = CASE WHEN %s THEN NOW() ELSE NULL END
                        WHERE id = %s""",
                    (new_remaining, is_closed, is_closed, lot["id"]),
                )
                remaining_to_sell -= consume

            # Record realized P&L
            proceeds = args.quantity * fill_price
            fees = Decimal(str(fee_cost))
            pnl = proceeds - total_cost - fees
            pnl_pct = min((pnl / total_cost * 100), Decimal("999999")) if total_cost > 0 else Decimal("0")

            conn.execute(
                f"""INSERT INTO {s}.pnl_realized
                    (sell_order_id, sell_execution_id, asset_id, strategy_id, venue_id,
                     quantity, cost_basis_usd, proceeds_usd, fees_usd, pnl_usd, pnl_pct)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (order["id"], execution["id"], asset_id, strategy_id, venue_id,
                 args.quantity, total_cost, proceeds, fees, pnl, pnl_pct),
            )

        conn.commit()

    output({
        "status": "ok",
        "order_id": order["id"],
        "side": "sell",
        "symbol": args.symbol.upper(),
        "quantity": float(args.quantity),
        "paper": paper,
    })


def cmd_cancel(args):
    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(
            f"""SELECT id, exchange_order_id, paper, asset_id, venue_id
                FROM {s}.orders WHERE id = %s AND status = 'open'""",
            (args.order_id,),
        )
        order = cur.fetchone()
        if not order:
            error(f"Order {args.order_id} not found or not open")

        # Cancel on exchange if live order with exchange_order_id
        if not order["paper"] and order["exchange_order_id"]:
            from core.exchange import CcxtExchange
            ex = CcxtExchange()
            # Get account address for sub-account exchanges
            cur = conn.execute(
                f"""SELECT acc.address FROM {s}.orders o
                    JOIN {s}.accounts acc ON acc.id = o.account_id
                    WHERE o.id = %s""",
                (args.order_id,),
            )
            acc = cur.fetchone()
            account_addr = acc["address"] if acc else None

            # Resolve symbol from asset
            cur = conn.execute(f"SELECT symbol FROM {s}.assets WHERE id = %s", (order["asset_id"],))
            asset = cur.fetchone()
            symbol = f"{asset['symbol']}/USDT" if asset else None

            try:
                ex.cancel_order(order["exchange_order_id"], symbol, account_address=account_addr)
            except Exception as e:
                error(f"Exchange cancel failed: {e}")

        conn.execute(
            f"""UPDATE {s}.orders SET status = 'cancelled', cancelled_at = NOW()
                WHERE id = %s""",
            (args.order_id,),
        )
        conn.execute(
            f"""INSERT INTO {s}.order_events (order_id, from_status, to_status, reason, changed_by)
                VALUES (%s, 'open', 'cancelled', %s, 'robin')""",
            (args.order_id, args.reason or "cancelled by agent"),
        )
        conn.commit()
    output({"status": "ok", "order_id": args.order_id, "cancelled": True})


def cmd_list_orders(args):
    s = schema()
    with sync_connect() as conn:
        conditions = []
        params = []
        if args.status:
            conditions.append("o.status = %s")
            params.append(args.status)
        if args.symbol:
            conditions.append("a.symbol = %s")
            params.append(args.symbol.upper())

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        cur = conn.execute(
            f"""SELECT o.id, a.symbol, o.side, o.type, o.quantity, o.price,
                       o.stop_loss, o.take_profit, o.status, o.paper,
                       o.created_at, o.filled_at, o.rationale
                FROM {s}.orders o
                JOIN {s}.assets a ON a.id = o.asset_id
                {where}
                ORDER BY o.created_at DESC LIMIT 50""",
            params,
        )
        rows = cur.fetchall()
    output([dict(r) for r in rows])


def main():
    parser = argparse.ArgumentParser(prog="python -m cli.trade", description="Trade CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("buy")
    p.add_argument("--symbol", required=True)
    p.add_argument("--venue", required=True)
    p.add_argument("--amount", type=Decimal, required=True, help="Amount in USD")
    p.add_argument("--price", type=Decimal, default=None)
    p.add_argument("--stop-loss", type=Decimal, default=None)
    p.add_argument("--take-profit", type=Decimal, default=None)
    p.add_argument("--strategy", default=None)
    p.add_argument("--rationale", default=None)
    p.add_argument("--live", action="store_true", help="Force live mode (skip paper fill)")

    p = sub.add_parser("sell")
    p.add_argument("--symbol", required=True)
    p.add_argument("--venue", required=True)
    p.add_argument("--quantity", type=Decimal, required=True)
    p.add_argument("--price", type=Decimal, default=None)
    p.add_argument("--strategy", default=None)
    p.add_argument("--rationale", default=None)
    p.add_argument("--live", action="store_true", help="Force live mode (skip paper fill)")

    p = sub.add_parser("cancel")
    p.add_argument("--order-id", type=int, required=True)
    p.add_argument("--reason", default=None)

    p = sub.add_parser("list-orders")
    p.add_argument("--status", default=None)
    p.add_argument("--symbol", default=None)

    args = parser.parse_args()
    commands = {"buy": cmd_buy, "sell": cmd_sell, "cancel": cmd_cancel, "list-orders": cmd_list_orders}
    commands[args.command](args)


if __name__ == "__main__":
    main()
