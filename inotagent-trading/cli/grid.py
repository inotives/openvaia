"""Grid cycle management CLI — open, monitor, close DCA grid cycles.

Usage:
    python -m cli.grid open --asset BTC --venue cryptocom
    python -m cli.grid status
    python -m cli.grid close --cycle-id grid-btc-...
    python -m cli.grid cancel --cycle-id grid-btc-...
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from decimal import Decimal

from cli import error, output
from core.db import schema, sync_connect
from core.exchange import CcxtExchange
from strategies.dca_grid import (
    GridCycle,
    compute_batch_tp_price,
    create_cycle,
    should_open_cycle,
)


GRID_METADATA_TABLE = "orders"  # Grid state stored as JSONB in a special order row


def _get_active_cycles(conn, s: str, asset_symbol: str | None = None) -> list[dict]:
    """Load active/expired_pending grid cycles from DB."""
    conditions = ["o.rationale LIKE 'grid_cycle:%%'", "o.status IN ('open', 'filled')"]
    params = []
    if asset_symbol:
        conditions.append("a.symbol = %s")
        params.append(asset_symbol.upper())

    cur = conn.execute(
        f"""SELECT o.id, o.rationale, o.created_at, a.symbol
            FROM {s}.orders o
            JOIN {s}.assets a ON a.id = o.asset_id
            WHERE {' AND '.join(conditions)}
            ORDER BY o.created_at DESC""",
        params,
    )
    cycles = []
    for row in cur.fetchall():
        try:
            cycle_data = json.loads(row["rationale"].replace("grid_cycle:", "", 1))
            cycle_data["db_order_id"] = row["id"]
            cycle_data["asset"] = row["symbol"]
            cycles.append(cycle_data)
        except (json.JSONDecodeError, AttributeError):
            continue
    return cycles


def _save_cycle(conn, s: str, cycle: GridCycle, asset_id: int, venue_id: int) -> int:
    """Save grid cycle state as a special order row."""
    cycle_json = json.dumps(cycle.to_json())
    cur = conn.execute(
        f"""INSERT INTO {s}.orders
            (asset_id, venue_id, side, type, quantity, price, status, paper, rationale, created_by)
            VALUES (%s, %s, 'buy', 'limit', 0, 0, 'open', true, %s, 'grid')
            RETURNING id""",
        (asset_id, venue_id, f"grid_cycle:{cycle_json}"),
    )
    return cur.fetchone()["id"]


def _update_cycle(conn, s: str, db_order_id: int, cycle: GridCycle):
    """Update grid cycle state."""
    cycle_json = json.dumps(cycle.to_json())
    status = "open" if cycle.status == "active" else "filled"
    conn.execute(
        f"UPDATE {s}.orders SET rationale = %s, status = %s WHERE id = %s",
        (f"grid_cycle:{cycle_json}", status, db_order_id),
    )


def cmd_open(args):
    """Open a new grid cycle for an asset."""
    s = schema()
    with sync_connect() as conn:
        # Resolve asset
        cur = conn.execute(f"SELECT id FROM {s}.assets WHERE symbol = %s", (args.asset.upper(),))
        asset = cur.fetchone()
        if not asset:
            error(f"Asset '{args.asset}' not found")

        # Resolve venue
        cur = conn.execute(f"SELECT id FROM {s}.venues WHERE code = %s", (args.venue,))
        venue = cur.fetchone()
        if not venue:
            error(f"Venue '{args.venue}' not found")

        # Get latest daily indicators
        cur = conn.execute(
            f"""SELECT rsi_14, atr_14, regime_score, close
                FROM {s}.indicators_daily i
                JOIN {s}.ohlcv_daily d ON d.asset_id = i.asset_id AND d.date = i.date
                WHERE i.asset_id = %s
                ORDER BY i.date DESC LIMIT 1""",
            (asset["id"],),
        )
        indicators = cur.fetchone()
        if not indicators:
            error("No daily indicators found")

        # Use lateral join for ohlcv to avoid duplicate
        cur = conn.execute(
            f"""SELECT d.close FROM {s}.ohlcv_daily d
                WHERE d.asset_id = %s ORDER BY d.date DESC LIMIT 1""",
            (asset["id"],),
        )
        price_row = cur.fetchone()
        if not price_row:
            error("No price data")

        current_price = Decimal(str(price_row["close"]))
        atr = Decimal(str(indicators["atr_14"])) if indicators["atr_14"] else Decimal("0")
        rsi = float(indicators["rsi_14"]) if indicators["rsi_14"] else None
        regime = float(indicators["regime_score"]) if indicators["regime_score"] else 50
        atr_pct = float(atr / current_price * 100) if current_price > 0 else 0

        # Load strategy params
        cur = conn.execute(
            f"""SELECT params FROM {s}.strategies
                WHERE asset_id = %s AND type = 'dca_grid' AND is_current = true""",
            (asset["id"],),
        )
        strat = cur.fetchone()
        if not strat:
            error(f"No dca_grid strategy found for {args.asset}. Create one first.")
        params = strat["params"] if isinstance(strat["params"], dict) else json.loads(strat["params"])

        # Check active cycles
        active_cycles = _get_active_cycles(conn, s, args.asset)
        active_count = len([c for c in active_cycles if c.get("status") == "active"])
        expired_count = len([c for c in active_cycles if c.get("status") == "expired_pending"])

        # Check entry conditions
        can_open, reason = should_open_cycle(
            regime, rsi, atr_pct, active_count > 0, expired_count, params
        )
        if not can_open:
            output({"status": "skipped", "reason": reason})
            return

        # Get portfolio value for capital calculation
        cur = conn.execute(f"SELECT COALESCE(SUM(balance_usd), 0) AS total FROM {s}.balances")
        portfolio = cur.fetchone()["total"] or Decimal("1000")

        capital_pct = Decimal(str(params.get("position", {}).get("capital_per_cycle_pct", 10))) / 100
        capital = portfolio * capital_pct

        # Get maker fee from trading_pairs
        cur = conn.execute(
            f"""SELECT maker_fee FROM {s}.trading_pairs
                WHERE base_asset_id = %s AND venue_id = %s AND is_current = true""",
            (asset["id"], venue["id"]),
        )
        fee_row = cur.fetchone()
        maker_fee = Decimal(str(fee_row["maker_fee"])) if fee_row and fee_row["maker_fee"] else Decimal("0.0024")

        # Create cycle
        cycle = create_cycle(
            args.asset.upper(), args.venue, current_price, atr,
            capital, regime, params, maker_fee=maker_fee,
        )
        if not cycle:
            error("Could not create grid cycle (extreme volatility?)")

        # Place grid buy orders on exchange (paper mode — just record in DB)
        # For live: would call exchange.create_order for each level
        for level in cycle.levels:
            cur = conn.execute(
                f"""INSERT INTO {s}.orders
                    (asset_id, venue_id, side, type, quantity, price, status, paper,
                     rationale, created_by)
                    VALUES (%s, %s, 'buy', 'limit', %s, %s, 'open', true,
                            %s, 'grid')
                    RETURNING id""",
                (asset["id"], venue["id"], level.quantity, level.price,
                 f"grid:{cycle.cycle_id}:level:{level.level}"),
            )
            level.buy_order_id = cur.fetchone()["id"]

        # Save cycle state
        db_id = _save_cycle(conn, s, cycle, asset["id"], venue["id"])
        conn.commit()

        output({
            "status": "ok",
            "cycle_id": cycle.cycle_id,
            "mode": cycle.mode,
            "asset": args.asset.upper(),
            "levels": len(cycle.levels),
            "capital": float(capital),
            "stop_loss": float(cycle.stop_loss_price),
            "grid_prices": [float(l.price) for l in cycle.levels],
        })


def cmd_status(args):
    """Show all active grid cycles."""
    s = schema()
    with sync_connect() as conn:
        cycles = _get_active_cycles(conn, s, args.asset if hasattr(args, 'asset') and args.asset else None)

    if not cycles:
        output({"cycles": [], "message": "No active grid cycles"})
        return

    output({"cycles": cycles})


def cmd_cancel(args):
    """Cancel a grid cycle — cancel all open orders."""
    s = schema()
    with sync_connect() as conn:
        cycles = _get_active_cycles(conn, s)
        target = None
        for c in cycles:
            if c.get("cycle_id") == args.cycle_id:
                target = c
                break

        if not target:
            error(f"Cycle '{args.cycle_id}' not found")

        # Cancel all open grid orders for this cycle
        cur = conn.execute(
            f"""UPDATE {s}.orders SET status = 'cancelled', cancelled_at = NOW()
                WHERE rationale LIKE %s AND status = 'open'
                RETURNING id""",
            (f"grid:{args.cycle_id}%",),
        )
        cancelled = cur.fetchall()

        # Update cycle state to closed
        target["status"] = "closed"
        target["close_reason"] = args.reason or "manual cancel"
        conn.execute(
            f"UPDATE {s}.orders SET rationale = %s, status = 'filled' WHERE id = %s",
            (f"grid_cycle:{json.dumps(target)}", target["db_order_id"]),
        )
        conn.commit()

        output({
            "status": "ok",
            "cycle_id": args.cycle_id,
            "orders_cancelled": len(cancelled),
        })


def main():
    parser = argparse.ArgumentParser(prog="python -m cli.grid", description="Grid cycle management")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("open")
    p.add_argument("--asset", required=True)
    p.add_argument("--venue", default="cryptocom")

    p = sub.add_parser("status")
    p.add_argument("--asset", default=None)

    p = sub.add_parser("cancel")
    p.add_argument("--cycle-id", required=True)
    p.add_argument("--reason", default=None)

    args = parser.parse_args()
    commands = {"open": cmd_open, "status": cmd_status, "cancel": cmd_cancel}
    commands[args.command](args)


if __name__ == "__main__":
    main()
