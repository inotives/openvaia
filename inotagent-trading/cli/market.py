"""Market data CLI — setup commands, data queries, seeding.

Usage:
    python -m cli.market <command> [args]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from cli import error, output
from core.db import schema, sync_connect


def cmd_add_asset(args):
    s = schema()
    with sync_connect() as conn:
        conn.execute(
            f"""INSERT INTO {s}.assets (symbol, name, created_by)
                VALUES (%(symbol)s, %(name)s, 'cli')
                ON CONFLICT (symbol) DO NOTHING""",
            {"symbol": args.symbol.upper(), "name": args.name},
        )
        conn.commit()
    output({"status": "ok", "asset": args.symbol.upper()})


def cmd_add_venue(args):
    s = schema()
    with sync_connect() as conn:
        conn.execute(
            f"""INSERT INTO {s}.venues (code, name, type, ccxt_id, created_by)
                VALUES (%(code)s, %(name)s, %(type)s, %(ccxt_id)s, 'cli')
                ON CONFLICT (code) DO NOTHING""",
            {"code": args.code, "name": args.name, "type": args.type, "ccxt_id": args.ccxt_id},
        )
        conn.commit()
    output({"status": "ok", "venue": args.code})


def cmd_add_mapping(args):
    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(f"SELECT id FROM {s}.assets WHERE symbol = %s", (args.asset.upper(),))
        asset = cur.fetchone()
        if not asset:
            error(f"Asset '{args.asset}' not found")

        cur = conn.execute(f"SELECT id FROM {s}.venues WHERE code = %s", (args.venue,))
        venue = cur.fetchone()
        if not venue:
            error(f"Venue '{args.venue}' not found")

        conn.execute(
            f"""INSERT INTO {s}.asset_mappings (asset_id, venue_id, external_id, created_by)
                VALUES (%s, %s, %s, 'cli')
                ON CONFLICT (asset_id, venue_id, COALESCE(network_id, 0)) DO NOTHING""",
            (asset["id"], venue["id"], args.external_id),
        )
        conn.commit()
    output({"status": "ok", "asset": args.asset, "venue": args.venue, "external_id": args.external_id})


def cmd_add_network(args):
    s = schema()
    with sync_connect() as conn:
        conn.execute(
            f"""INSERT INTO {s}.networks (code, name, chain_id, native_asset, created_by)
                VALUES (%(code)s, %(name)s, %(chain_id)s, %(native_asset)s, 'cli')
                ON CONFLICT (code) DO NOTHING""",
            {"code": args.code, "name": args.name, "chain_id": args.chain_id, "native_asset": args.native_asset},
        )
        conn.commit()
    output({"status": "ok", "network": args.code})


def cmd_add_network_mapping(args):
    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(f"SELECT id FROM {s}.networks WHERE code = %s", (args.network,))
        network = cur.fetchone()
        if not network:
            error(f"Network '{args.network}' not found")

        cur = conn.execute(f"SELECT id FROM {s}.venues WHERE code = %s", (args.venue,))
        venue = cur.fetchone()
        if not venue:
            error(f"Venue '{args.venue}' not found")

        conn.execute(
            f"""INSERT INTO {s}.network_mappings (network_id, venue_id, external_id, created_by)
                VALUES (%s, %s, %s, 'cli')
                ON CONFLICT (network_id, venue_id) DO NOTHING""",
            (network["id"], venue["id"], args.external_id),
        )
        conn.commit()
    output({"status": "ok", "network": args.network, "venue": args.venue})


def cmd_add_trading_pair(args):
    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(f"SELECT id FROM {s}.venues WHERE code = %s", (args.venue,))
        venue = cur.fetchone()
        if not venue:
            error(f"Venue '{args.venue}' not found")

        cur = conn.execute(f"SELECT id FROM {s}.assets WHERE symbol = %s", (args.base.upper(),))
        base = cur.fetchone()
        if not base:
            error(f"Base asset '{args.base}' not found")

        cur = conn.execute(f"SELECT id FROM {s}.assets WHERE symbol = %s", (args.quote.upper(),))
        quote = cur.fetchone()
        if not quote:
            error(f"Quote asset '{args.quote}' not found")

        conn.execute(
            f"""INSERT INTO {s}.trading_pairs
                (venue_id, base_asset_id, quote_asset_id, pair_symbol,
                 min_order_size, price_precision, qty_precision, maker_fee, taker_fee, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'cli')
                ON CONFLICT (venue_id, base_asset_id, quote_asset_id, version) DO NOTHING""",
            (venue["id"], base["id"], quote["id"], args.pair_symbol,
             args.min_order, args.price_precision, args.qty_precision,
             args.maker_fee, args.taker_fee),
        )
        conn.commit()
    output({"status": "ok", "pair": args.pair_symbol, "venue": args.venue})


def cmd_add_account(args):
    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(f"SELECT id FROM {s}.venues WHERE code = %s", (args.venue,))
        venue = cur.fetchone()
        if not venue:
            error(f"Venue '{args.venue}' not found")

        network_id = None
        if args.network:
            cur = conn.execute(f"SELECT id FROM {s}.networks WHERE code = %s", (args.network,))
            net = cur.fetchone()
            if not net:
                error(f"Network '{args.network}' not found")
            network_id = net["id"]

        conn.execute(
            f"""INSERT INTO {s}.accounts
                (venue_id, name, account_type, address, network_id, is_default, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, 'cli')
                ON CONFLICT (venue_id, name, COALESCE(address, ''), COALESCE(network_id, 0)) DO NOTHING""",
            (venue["id"], args.name, args.type, args.address, network_id, args.default),
        )
        conn.commit()
    output({"status": "ok", "account": f"{args.venue}:{args.name}"})


def cmd_overview(args):
    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(
            f"""SELECT a.symbol, a.name,
                       d.close AS price, d.date AS price_date,
                       i.rsi_14, i.ema_50, i.ema_200, i.adx_14, i.regime_score
                FROM {s}.assets a
                LEFT JOIN LATERAL (
                    SELECT close, date FROM {s}.ohlcv_daily
                    WHERE asset_id = a.id ORDER BY date DESC LIMIT 1
                ) d ON true
                LEFT JOIN LATERAL (
                    SELECT rsi_14, ema_50, ema_200, adx_14, regime_score
                    FROM {s}.indicators_daily
                    WHERE asset_id = a.id ORDER BY date DESC LIMIT 1
                ) i ON true
                WHERE a.is_active = true AND a.deleted_at IS NULL
                ORDER BY a.symbol"""
        )
        rows = cur.fetchall()

    output([dict(r) for r in rows])


def cmd_price(args):
    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(
            f"""SELECT o.close, o.bid, o.ask, o.spread_pct, o.volume, o.timestamp
                FROM {s}.ohlcv_1m o
                JOIN {s}.assets a ON a.id = o.asset_id
                WHERE a.symbol = %s
                ORDER BY o.timestamp DESC LIMIT 1""",
            (args.symbol.upper(),),
        )
        row = cur.fetchone()

    if not row:
        error(f"No price data for {args.symbol}")
    output(dict(row))


def cmd_ta(args):
    s = schema()
    with sync_connect() as conn:
        # Daily TA
        cur = conn.execute(
            f"""SELECT * FROM {s}.indicators_daily
                WHERE asset_id = (SELECT id FROM {s}.assets WHERE symbol = %s)
                ORDER BY date DESC LIMIT 1""",
            (args.symbol.upper(),),
        )
        daily = cur.fetchone()

        # Intraday TA
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


def cmd_history(args):
    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(
            f"""SELECT date, open, high, low, close, volume
                FROM {s}.ohlcv_daily
                WHERE asset_id = (SELECT id FROM {s}.assets WHERE symbol = %s)
                ORDER BY date DESC LIMIT %s""",
            (args.symbol.upper(), args.days),
        )
        rows = cur.fetchall()

    output([dict(r) for r in rows])


def cmd_seed_daily(args):
    """Import daily OHLCV from CSV file."""
    s = schema()
    filepath = Path(args.file)
    if not filepath.exists():
        error(f"File not found: {args.file}")

    with sync_connect() as conn:
        # Resolve asset_id
        cur = conn.execute(f"SELECT id FROM {s}.assets WHERE symbol = %s", (args.asset.upper(),))
        asset = cur.fetchone()
        if not asset:
            error(f"Asset '{args.asset}' not found. Run add-asset first.")
        asset_id = asset["id"]

        # Resolve venue_id
        cur = conn.execute(f"SELECT id FROM {s}.venues WHERE code = %s", (args.venue,))
        venue = cur.fetchone()
        if not venue:
            error(f"Venue '{args.venue}' not found. Run add-venue first.")
        venue_id = venue["id"]

        count = 0
        with open(filepath, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Support CoinMarketCap CSV format
                dt = row.get("timeOpen", row.get("date", ""))[:10]
                if not dt:
                    continue

                conn.execute(
                    f"""INSERT INTO {s}.ohlcv_daily
                        (asset_id, venue_id, date, open, high, low, close, volume, market_cap)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (asset_id, venue_id, date) DO NOTHING""",
                    (
                        asset_id, venue_id, dt,
                        Decimal(row.get("open", "0").replace(",", "")),
                        Decimal(row.get("high", "0").replace(",", "")),
                        Decimal(row.get("low", "0").replace(",", "")),
                        Decimal(row.get("close", "0").replace(",", "")),
                        Decimal(row.get("volume", "0").replace(",", "")),
                        Decimal(row["marketCap"].replace(",", "")) if row.get("marketCap") else None,
                    ),
                )
                count += 1

        conn.commit()
    output({"status": "ok", "asset": args.asset, "venue": args.venue, "rows_imported": count})


def cmd_coverage(args):
    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(
            f"""SELECT a.symbol,
                   (SELECT MIN(date) FROM {s}.ohlcv_daily WHERE asset_id = a.id) AS daily_from,
                   (SELECT MAX(date) FROM {s}.ohlcv_daily WHERE asset_id = a.id) AS daily_to,
                   (SELECT COUNT(*) FROM {s}.ohlcv_daily WHERE asset_id = a.id) AS daily_rows,
                   (SELECT MIN(date) FROM {s}.indicators_daily WHERE asset_id = a.id) AS ta_from,
                   (SELECT MAX(date) FROM {s}.indicators_daily WHERE asset_id = a.id) AS ta_to,
                   (SELECT COUNT(*) FROM {s}.indicators_daily WHERE asset_id = a.id) AS ta_rows,
                   (SELECT MIN(timestamp) FROM {s}.ohlcv_1m WHERE asset_id = a.id) AS m1_from,
                   (SELECT MAX(timestamp) FROM {s}.ohlcv_1m WHERE asset_id = a.id) AS m1_to,
                   (SELECT COUNT(*) FROM {s}.ohlcv_1m WHERE asset_id = a.id) AS m1_rows
                FROM {s}.assets a
                WHERE a.is_active = true AND a.deleted_at IS NULL
                ORDER BY a.symbol"""
        )
        rows = cur.fetchall()

    output({r["symbol"]: {k: v for k, v in dict(r).items() if k != "symbol"} for r in rows})


def cmd_poller_status(args):
    """Read poller health status from JSON file."""
    from pathlib import Path
    status_file = Path(".poller_status.json")
    if not status_file.exists():
        status_file = Path("/opt/inotagent-trading/.poller_status.json")
    if not status_file.exists():
        error("No poller status file found")
    output(json.loads(status_file.read_text()))


def main():
    parser = argparse.ArgumentParser(prog="python -m cli.market", description="Market data CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # Setup commands
    p = sub.add_parser("add-asset")
    p.add_argument("--symbol", required=True)
    p.add_argument("--name", default=None)

    p = sub.add_parser("add-venue")
    p.add_argument("--code", required=True)
    p.add_argument("--name", default=None)
    p.add_argument("--type", required=True, choices=["exchange", "data", "wallet", "explorer"])
    p.add_argument("--ccxt-id", default=None)

    p = sub.add_parser("add-mapping")
    p.add_argument("--asset", required=True)
    p.add_argument("--venue", required=True)
    p.add_argument("--external-id", required=True)

    p = sub.add_parser("add-network")
    p.add_argument("--code", required=True)
    p.add_argument("--name", default=None)
    p.add_argument("--chain-id", type=int, default=None)
    p.add_argument("--native-asset", default=None)

    p = sub.add_parser("add-network-mapping")
    p.add_argument("--network", required=True)
    p.add_argument("--venue", required=True)
    p.add_argument("--external-id", required=True)

    p = sub.add_parser("add-trading-pair")
    p.add_argument("--venue", required=True)
    p.add_argument("--base", required=True)
    p.add_argument("--quote", required=True)
    p.add_argument("--pair-symbol", required=True)
    p.add_argument("--min-order", type=Decimal, default=None)
    p.add_argument("--price-precision", type=int, default=None)
    p.add_argument("--qty-precision", type=int, default=None)
    p.add_argument("--maker-fee", type=Decimal, default=None)
    p.add_argument("--taker-fee", type=Decimal, default=None)

    p = sub.add_parser("add-account")
    p.add_argument("--venue", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--type", required=True, choices=["spot", "margin", "futures", "earn", "wallet"])
    p.add_argument("--address", default=None)
    p.add_argument("--network", default=None)
    p.add_argument("--default", action="store_true")

    # Data commands
    sub.add_parser("overview")

    p = sub.add_parser("price")
    p.add_argument("--symbol", required=True)

    p = sub.add_parser("ta")
    p.add_argument("--symbol", required=True)

    p = sub.add_parser("history")
    p.add_argument("--symbol", required=True)
    p.add_argument("--days", type=int, default=30)

    p = sub.add_parser("seed-daily")
    p.add_argument("--asset", required=True)
    p.add_argument("--venue", required=True)
    p.add_argument("--file", required=True)

    sub.add_parser("coverage")
    sub.add_parser("poller-status")

    args = parser.parse_args()

    commands = {
        "add-asset": cmd_add_asset,
        "add-venue": cmd_add_venue,
        "add-mapping": cmd_add_mapping,
        "add-network": cmd_add_network,
        "add-network-mapping": cmd_add_network_mapping,
        "add-trading-pair": cmd_add_trading_pair,
        "add-account": cmd_add_account,
        "overview": cmd_overview,
        "price": cmd_price,
        "ta": cmd_ta,
        "history": cmd_history,
        "seed-daily": cmd_seed_daily,
        "coverage": cmd_coverage,
        "poller-status": cmd_poller_status,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
