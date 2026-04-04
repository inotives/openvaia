"""Strategy CLI — create, view, update, activate, set mode.

Usage:
    python -m cli.strategy <command> [args]
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal

from cli import error, output
from core.db import schema, sync_connect


def cmd_list(args):
    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(
            f"""SELECT s.name, s.type, s.is_active, s.paper_mode, s.version, s.valid_from,
                       a.symbol AS asset, v.code AS venue
                FROM {s}.strategies s
                LEFT JOIN {s}.assets a ON a.id = s.asset_id
                LEFT JOIN {s}.venues v ON v.id = s.venue_id
                WHERE s.is_current = true
                ORDER BY s.name"""
        )
        rows = cur.fetchall()
    output([dict(r) for r in rows])


def cmd_create(args):
    s = schema()
    params = json.loads(args.params) if args.params else {}

    with sync_connect() as conn:
        # Resolve asset
        asset_id = None
        if args.asset:
            cur = conn.execute(f"SELECT id FROM {s}.assets WHERE symbol = %s", (args.asset.upper(),))
            row = cur.fetchone()
            if not row:
                error(f"Asset '{args.asset}' not found")
            asset_id = row["id"]

        # Resolve venue
        venue_id = None
        if args.venue:
            cur = conn.execute(f"SELECT id FROM {s}.venues WHERE code = %s", (args.venue,))
            row = cur.fetchone()
            if not row:
                error(f"Venue '{args.venue}' not found")
            venue_id = row["id"]

        # Check name doesn't exist
        cur = conn.execute(
            f"SELECT 1 FROM {s}.strategies WHERE name = %s AND is_current = true", (args.name,)
        )
        if cur.fetchone():
            error(f"Strategy '{args.name}' already exists")

        conn.execute(
            f"""INSERT INTO {s}.strategies
                (name, type, asset_id, venue_id, params, paper_mode, created_by)
                VALUES (%s, %s, %s, %s, %s, true, 'cli')""",
            (args.name, args.type, asset_id, venue_id, json.dumps(params)),
        )
        conn.commit()
    output({"status": "ok", "strategy": args.name, "paper_mode": True})


def cmd_view(args):
    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(
            f"""SELECT s.*, a.symbol AS asset, v.code AS venue
                FROM {s}.strategies s
                LEFT JOIN {s}.assets a ON a.id = s.asset_id
                LEFT JOIN {s}.venues v ON v.id = s.venue_id
                WHERE s.name = %s AND s.is_current = true""",
            (args.name,),
        )
        row = cur.fetchone()

    if not row:
        error(f"Strategy '{args.name}' not found")
    output(dict(row))


def cmd_history(args):
    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(
            f"""SELECT version, is_current, valid_from, valid_to, params, is_active, paper_mode
                FROM {s}.strategies WHERE name = %s ORDER BY version DESC""",
            (args.name,),
        )
        rows = cur.fetchall()

    if not rows:
        error(f"Strategy '{args.name}' not found")
    output([dict(r) for r in rows])


def cmd_update(args):
    """SCD Type 2 update: close current version, create new version with updated params."""
    s = schema()
    param_updates = {}
    if args.param:
        for p in args.param:
            key, _, value = p.partition("=")
            try:
                param_updates[key] = json.loads(value)
            except json.JSONDecodeError:
                param_updates[key] = value

    with sync_connect() as conn:
        cur = conn.execute(
            f"SELECT * FROM {s}.strategies WHERE name = %s AND is_current = true", (args.name,)
        )
        current = cur.fetchone()
        if not current:
            error(f"Strategy '{args.name}' not found")

        current = dict(current)
        new_params = json.loads(current["params"]) if isinstance(current["params"], str) else current["params"]

        # Apply param updates (supports nested keys like entry.rsi_buy)
        for key, value in param_updates.items():
            parts = key.split(".")
            target = new_params
            for part in parts[:-1]:
                target = target.setdefault(part, {})
            target[parts[-1]] = value

        new_version = current["version"] + 1

        # Close current version
        conn.execute(
            f"""UPDATE {s}.strategies SET is_current = false, valid_to = NOW()
                WHERE id = %s""",
            (current["id"],),
        )

        # Insert new version
        conn.execute(
            f"""INSERT INTO {s}.strategies
                (name, type, asset_id, venue_id, params, is_active, paper_mode,
                 version, valid_from, is_current, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), true, 'cli')""",
            (current["name"], current["type"], current["asset_id"], current["venue_id"],
             json.dumps(new_params), current["is_active"], current["paper_mode"], new_version),
        )
        conn.commit()

    output({"status": "ok", "strategy": args.name, "version": new_version, "params_updated": list(param_updates.keys())})


def cmd_activate(args):
    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(
            f"UPDATE {s}.strategies SET is_active = true WHERE name = %s AND is_current = true RETURNING name",
            (args.name,),
        )
        if not cur.fetchone():
            error(f"Strategy '{args.name}' not found")
        conn.commit()
    output({"status": "ok", "strategy": args.name, "is_active": True})


def cmd_deactivate(args):
    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(
            f"UPDATE {s}.strategies SET is_active = false WHERE name = %s AND is_current = true RETURNING name",
            (args.name,),
        )
        if not cur.fetchone():
            error(f"Strategy '{args.name}' not found")
        conn.commit()
    output({"status": "ok", "strategy": args.name, "is_active": False})


def cmd_set_mode(args):
    s = schema()
    paper = args.mode == "paper"
    with sync_connect() as conn:
        cur = conn.execute(
            f"UPDATE {s}.strategies SET paper_mode = %s WHERE name = %s AND is_current = true RETURNING name",
            (paper, args.name),
        )
        if not cur.fetchone():
            error(f"Strategy '{args.name}' not found")
        conn.commit()
    output({"status": "ok", "strategy": args.name, "mode": args.mode})


def main():
    parser = argparse.ArgumentParser(prog="python -m cli.strategy", description="Strategy CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list")

    p = sub.add_parser("create")
    p.add_argument("--name", required=True)
    p.add_argument("--type", required=True)
    p.add_argument("--asset", default=None)
    p.add_argument("--venue", default=None)
    p.add_argument("--params", default=None, help="JSON string of strategy params")

    p = sub.add_parser("view")
    p.add_argument("--name", required=True)

    p = sub.add_parser("history")
    p.add_argument("--name", required=True)

    p = sub.add_parser("update")
    p.add_argument("--name", required=True)
    p.add_argument("--param", action="append", help="key=value (repeatable, supports nested: entry.rsi_buy=25)")

    p = sub.add_parser("activate")
    p.add_argument("--name", required=True)

    p = sub.add_parser("deactivate")
    p.add_argument("--name", required=True)

    p = sub.add_parser("set-mode")
    p.add_argument("--name", required=True)
    p.add_argument("--mode", required=True, choices=["paper", "live"])

    args = parser.parse_args()

    commands = {
        "list": cmd_list, "create": cmd_create, "view": cmd_view, "history": cmd_history,
        "update": cmd_update, "activate": cmd_activate, "deactivate": cmd_deactivate,
        "set-mode": cmd_set_mode,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
