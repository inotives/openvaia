"""Portfolio CLI — balance, P&L, transfers, reconciliation.

Usage:
    python -m cli.portfolio <command> [args]
"""

from __future__ import annotations

import argparse
from decimal import Decimal

from cli import error, output
from core.db import schema, sync_connect


def cmd_balance(args):
    s = schema()
    with sync_connect() as conn:
        if args.venue:
            cur = conn.execute(
                f"""SELECT a.symbol, b.balance, b.available, b.locked, b.balance_usd, b.synced_at
                    FROM {s}.balances b
                    JOIN {s}.accounts acc ON acc.id = b.account_id
                    JOIN {s}.venues v ON v.id = acc.venue_id
                    JOIN {s}.assets a ON a.id = b.asset_id
                    WHERE v.code = %s AND acc.deleted_at IS NULL
                    ORDER BY b.balance_usd DESC NULLS LAST""",
                (args.venue,),
            )
        else:
            cur = conn.execute(
                f"""SELECT symbol, total_balance, total_available, total_locked, total_usd, venue_count
                    FROM {s}.total_balances ORDER BY total_usd DESC NULLS LAST"""
            )
        rows = cur.fetchall()

    if args.include_paper:
        with sync_connect() as conn:
            cur = conn.execute(
                f"""SELECT s.name AS strategy, a.symbol, pb.balance
                    FROM {s}.paper_balances pb
                    JOIN {s}.strategies s ON s.id = pb.strategy_id
                    JOIN {s}.assets a ON a.id = pb.asset_id
                    WHERE s.is_current = true
                    ORDER BY s.name, a.symbol"""
            )
            paper = cur.fetchall()
        output({"real": [dict(r) for r in rows], "paper": [dict(r) for r in paper]})
    else:
        output([dict(r) for r in rows])


def cmd_accounts(args):
    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(
            f"""SELECT acc.id, v.code AS venue, acc.name, acc.account_type,
                       acc.address, acc.is_default,
                       COALESCE(SUM(b.balance_usd), 0) AS total_usd
                FROM {s}.accounts acc
                JOIN {s}.venues v ON v.id = acc.venue_id
                LEFT JOIN {s}.balances b ON b.account_id = acc.id
                WHERE acc.deleted_at IS NULL
                GROUP BY acc.id, v.code, acc.name, acc.account_type, acc.address, acc.is_default
                ORDER BY v.code, acc.name"""
        )
        rows = cur.fetchall()
    output([dict(r) for r in rows])


def cmd_pnl(args):
    s = schema()
    period_filter = {
        "today": "created_at::date = CURRENT_DATE",
        "week": "created_at >= CURRENT_DATE - INTERVAL '7 days'",
        "month": "created_at >= CURRENT_DATE - INTERVAL '30 days'",
        "all": "true",
    }

    where = period_filter.get(args.period, period_filter["today"])

    with sync_connect() as conn:
        conditions = [where]
        params = []
        if args.strategy:
            conditions.append("s.name = %s")
            params.append(args.strategy)

        where_clause = " AND ".join(conditions)

        cur = conn.execute(
            f"""SELECT COALESCE(SUM(p.pnl_usd), 0) AS total_pnl,
                       COUNT(*) AS trades,
                       COUNT(*) FILTER (WHERE p.pnl_usd > 0) AS wins,
                       COUNT(*) FILTER (WHERE p.pnl_usd < 0) AS losses,
                       COALESCE(SUM(p.fees_usd), 0) AS total_fees,
                       COALESCE(AVG(p.pnl_pct), 0) AS avg_pnl_pct
                FROM {s}.pnl_realized p
                LEFT JOIN {s}.strategies s ON s.id = p.strategy_id
                WHERE {where_clause}""",
            params,
        )
        row = cur.fetchone()
    output(dict(row))


def cmd_transfers(args):
    s = schema()
    with sync_connect() as conn:
        conditions = ["true"]
        params = []

        if args.type:
            conditions.append("t.transfer_type = %s")
            params.append(args.type)
        if args.days:
            conditions.append(f"t.initiated_at >= CURRENT_DATE - INTERVAL '{int(args.days)} days'")

        where = " AND ".join(conditions)

        cur = conn.execute(
            f"""SELECT t.id, t.transfer_type, t.amount, t.amount_usd,
                       a.symbol AS asset, t.status, t.method,
                       fa.name AS from_account, ta.name AS to_account,
                       t.initiated_at, t.completed_at
                FROM {s}.transfers t
                JOIN {s}.assets a ON a.id = t.asset_id
                LEFT JOIN {s}.accounts fa ON fa.id = t.from_account_id
                LEFT JOIN {s}.accounts ta ON ta.id = t.to_account_id
                WHERE {where}
                ORDER BY t.initiated_at DESC LIMIT 50""",
            params,
        )
        rows = cur.fetchall()
    output([dict(r) for r in rows])


def cmd_transfer(args):
    """Record a transfer (deposit, withdrawal, internal)."""
    s = schema()
    with sync_connect() as conn:
        # Resolve asset
        cur = conn.execute(f"SELECT id FROM {s}.assets WHERE symbol = %s", (args.asset.upper(),))
        asset = cur.fetchone()
        if not asset:
            error(f"Asset '{args.asset}' not found")

        from_account_id = None
        to_account_id = None

        if args.from_account:
            venue, name = args.from_account.split(":", 1)
            cur = conn.execute(
                f"""SELECT acc.id FROM {s}.accounts acc
                    JOIN {s}.venues v ON v.id = acc.venue_id
                    WHERE v.code = %s AND acc.name = %s""",
                (venue, name),
            )
            row = cur.fetchone()
            if not row:
                error(f"Account '{args.from_account}' not found")
            from_account_id = row["id"]

        if args.to_account:
            venue, name = args.to_account.split(":", 1)
            cur = conn.execute(
                f"""SELECT acc.id FROM {s}.accounts acc
                    JOIN {s}.venues v ON v.id = acc.venue_id
                    WHERE v.code = %s AND acc.name = %s""",
                (venue, name),
            )
            row = cur.fetchone()
            if not row:
                error(f"Account '{args.to_account}' not found")
            to_account_id = row["id"]

        cur = conn.execute(
            f"""INSERT INTO {s}.transfers
                (transfer_type, from_account_id, to_account_id, to_address,
                 asset_id, amount, method, reference, status, initiated_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'completed', 'cli')
                RETURNING id""",
            (args.type, from_account_id, to_account_id, args.to_address,
             asset["id"], args.amount, args.method, args.reference),
        )
        transfer = cur.fetchone()
        conn.commit()

    output({"status": "ok", "transfer_id": transfer["id"]})


def cmd_snapshot(args):
    """Take a daily portfolio snapshot."""
    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(f"SELECT COALESCE(SUM(balance_usd), 0) AS total FROM {s}.balances")
        total = cur.fetchone()["total"]

        cur = conn.execute(
            f"""SELECT COALESCE(SUM(pnl_usd), 0) AS realized,
                       COALESCE(SUM(fees_usd), 0) AS fees
                FROM {s}.pnl_realized WHERE created_at::date = CURRENT_DATE"""
        )
        daily = cur.fetchone()

        conn.execute(
            f"""INSERT INTO {s}.portfolio_snapshots
                (date, total_value_usd, realized_pnl_day_usd, total_fees_day_usd)
                VALUES (CURRENT_DATE, %s, %s, %s)
                ON CONFLICT (date) DO UPDATE SET
                    total_value_usd = EXCLUDED.total_value_usd,
                    realized_pnl_day_usd = EXCLUDED.realized_pnl_day_usd,
                    total_fees_day_usd = EXCLUDED.total_fees_day_usd""",
            (total, daily["realized"], daily["fees"]),
        )
        conn.commit()
    output({"status": "ok", "date": "today", "total_value_usd": float(total)})


def cmd_benchmark(args):
    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(
            f"""SELECT date, total_value_usd, realized_pnl_day_usd, hodl_value_usd
                FROM {s}.portfolio_snapshots
                WHERE date >= CURRENT_DATE - INTERVAL '{int(args.days)} days'
                ORDER BY date"""
        )
        rows = cur.fetchall()
    output([dict(r) for r in rows])


def cmd_history(args):
    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(
            f"""SELECT o.id, a.symbol, o.side, o.quantity, o.price, o.status, o.paper,
                       o.rationale, o.created_at, o.filled_at,
                       e.price AS fill_price, e.fee, e.fee_currency
                FROM {s}.orders o
                JOIN {s}.assets a ON a.id = o.asset_id
                LEFT JOIN {s}.executions e ON e.order_id = o.id
                WHERE o.status = 'filled'
                ORDER BY o.filled_at DESC LIMIT %s""",
            (args.last or 20,),
        )
        rows = cur.fetchall()
    output([dict(r) for r in rows])


def cmd_reconcile_orders(args):
    s = schema()
    output({"status": "todo", "message": "Order reconciliation requires live exchange connection"})


def cmd_reconcile_pnl(args):
    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(f"SELECT * FROM {s}.balance_reconciliation")
        rows = cur.fetchall()
    output([dict(r) for r in rows])


def main():
    parser = argparse.ArgumentParser(prog="python -m cli.portfolio", description="Portfolio CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("balance")
    p.add_argument("--venue", default=None)
    p.add_argument("--include-paper", action="store_true")

    sub.add_parser("accounts")

    p = sub.add_parser("pnl")
    p.add_argument("--period", default="today", choices=["today", "week", "month", "all"])
    p.add_argument("--strategy", default=None)

    p = sub.add_parser("transfers")
    p.add_argument("--type", default=None, choices=["deposit", "withdrawal", "internal"])
    p.add_argument("--days", type=int, default=30)

    p = sub.add_parser("transfer")
    p.add_argument("--type", required=True, choices=["deposit", "withdrawal", "internal"])
    p.add_argument("--from-account", default=None, help="venue:name (e.g. cryptocom:main)")
    p.add_argument("--to-account", default=None, help="venue:name")
    p.add_argument("--to-address", default=None)
    p.add_argument("--asset", required=True)
    p.add_argument("--amount", type=Decimal, required=True)
    p.add_argument("--method", default=None)
    p.add_argument("--reference", default=None)

    sub.add_parser("snapshot")

    p = sub.add_parser("benchmark")
    p.add_argument("--days", type=int, default=7)

    p = sub.add_parser("history")
    p.add_argument("--last", type=int, default=20)

    p = sub.add_parser("reconcile-orders")
    p.add_argument("--venue", required=True)

    p = sub.add_parser("reconcile-pnl")
    p.add_argument("--days", type=int, default=30)

    args = parser.parse_args()
    commands = {
        "balance": cmd_balance, "accounts": cmd_accounts, "pnl": cmd_pnl,
        "transfers": cmd_transfers, "transfer": cmd_transfer, "snapshot": cmd_snapshot,
        "benchmark": cmd_benchmark, "history": cmd_history,
        "reconcile-orders": cmd_reconcile_orders, "reconcile-pnl": cmd_reconcile_pnl,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
