"""Market data CLI — setup commands, data queries, seeding.

Usage:
    python -m cli.market <command> [args]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime, timezone
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
        with open(filepath, newline="", encoding="utf-8-sig") as f:
            # Auto-detect delimiter (CoinMarketCap uses semicolons)
            sample = f.read(1024)
            f.seek(0)
            delimiter = ";" if ";" in sample.split("\n")[0] else ","
            reader = csv.DictReader(f, delimiter=delimiter)

            for row in reader:
                # Support CoinMarketCap CSV format (timeOpen) and generic (date)
                dt = row.get("timeOpen", row.get("date", ""))[:10]
                if not dt:
                    continue

                def _dec(val: str | None) -> Decimal | None:
                    if not val:
                        return None
                    return Decimal(val.strip().strip('"').replace(",", ""))

                conn.execute(
                    f"""INSERT INTO {s}.ohlcv_daily
                        (asset_id, venue_id, date, open, high, low, close, volume, market_cap)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (asset_id, venue_id, date) DO NOTHING""",
                    (
                        asset_id, venue_id, dt,
                        _dec(row.get("open")),
                        _dec(row.get("high")),
                        _dec(row.get("low")),
                        _dec(row.get("close")),
                        _dec(row.get("volume")),
                        _dec(row.get("marketCap")),
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


def cmd_backfill_daily_ta(args):
    """Compute daily TA indicators for all historical OHLCV data."""
    import pandas as pd
    from core.indicators import compute_daily

    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(f"SELECT id FROM {s}.assets WHERE symbol = %s", (args.asset.upper(),))
        asset = cur.fetchone()
        if not asset:
            error(f"Asset '{args.asset}' not found")
        asset_id = asset["id"]

        # Fetch all daily OHLCV
        cur = conn.execute(
            f"""SELECT date, open, high, low, close, volume
                FROM {s}.ohlcv_daily WHERE asset_id = %s ORDER BY date ASC""",
            (asset_id,),
        )
        rows = cur.fetchall()
        if len(rows) < 15:
            error(f"Insufficient data: {len(rows)} rows (need at least 15)")

        df = pd.DataFrame([dict(r) for r in rows])
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        indicators = compute_daily(df)

        # Standard columns (typed DB columns)
        cols = [
            "rsi_14", "rsi_7", "stoch_rsi_k", "stoch_rsi_d",
            "ema_9", "ema_12", "ema_20", "ema_26", "ema_50", "ema_200",
            "sma_50", "sma_200",
            "macd", "macd_signal", "macd_hist",
            "atr_14", "bb_upper", "bb_lower", "bb_width",
            "adx_14",
            "obv", "volume_sma_20", "volume_ratio",
            "regime_score",
        ]
        # Extra columns stored in custom JSONB (extensible, no migration needed)
        custom_cols = ["ema_8", "kc_upper", "kc_lower", "squeeze", "high_20d"]

        count = 0
        for i, row in indicators.iterrows():
            date_val = df.iloc[i]["date"]
            values = [asset_id, date_val]
            for col in cols:
                val = row.get(col)
                if pd.notna(val):
                    values.append(Decimal(str(round(float(val), 8))))
                else:
                    values.append(None)

            # Build custom JSONB
            custom = {}
            for col in custom_cols:
                val = row.get(col)
                if pd.notna(val):
                    custom[col] = round(float(val), 8)
            values.append(json.dumps(custom) if custom else "{}")

            all_cols = cols + ["custom"]
            placeholders = ", ".join(f"%s" for _ in values)
            col_names = "asset_id, date, " + ", ".join(all_cols)

            conn.execute(
                f"""INSERT INTO {s}.indicators_daily ({col_names})
                    VALUES ({placeholders})
                    ON CONFLICT (asset_id, date) DO UPDATE SET
                        {', '.join(f'{c} = EXCLUDED.{c}' for c in all_cols)}
                """,
                values,
            )
            count += 1

        conn.commit()

    output({"status": "ok", "asset": args.asset.upper(), "rows_computed": count})


def cmd_fetch_daily(args):
    """Fetch latest daily OHLCV from CoinGecko for all active assets."""
    import os
    import requests
    from datetime import timedelta

    # CoinGecko API key (Demo plan: 30 calls/min vs unauthenticated ~10/min)
    cg_api_key = os.environ.get("COINGECKO_API_KEY")
    cg_headers = {"x_cg_demo_api_key": cg_api_key} if cg_api_key else {}

    s = schema()
    with sync_connect() as conn:
        # Find coingecko venue
        cur = conn.execute(f"SELECT id FROM {s}.venues WHERE code = 'coingecko'")
        cg_venue = cur.fetchone()
        if not cg_venue:
            error("Venue 'coingecko' not found. Run: cli.market add-venue --code coingecko --name CoinGecko --type data")
        cg_venue_id = cg_venue["id"]

        # Get all active assets with coingecko mapping
        cur = conn.execute(
            f"""SELECT a.id AS asset_id, a.symbol, am.external_id AS coingecko_id
                FROM {s}.assets a
                JOIN {s}.asset_mappings am ON am.asset_id = a.id AND am.venue_id = %s
                WHERE a.is_active = true AND a.deleted_at IS NULL AND am.is_active = true""",
            (cg_venue_id,),
        )
        assets = cur.fetchall()

        if not assets:
            error("No assets with CoinGecko mapping found. Run: cli.market add-mapping --asset CRO --venue coingecko --external-id crypto-com-chain")

        # ── Fetch 24h volume for all assets in one call ──
        coingecko_ids = [a["coingecko_id"] for a in assets]
        volume_map = {}  # coingecko_id → 24h volume in USD
        try:
            resp = requests.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                params={"vs_currency": "usd", "ids": ",".join(coingecko_ids)},
                headers=cg_headers,
                timeout=30,
            )
            resp.raise_for_status()
            for coin in resp.json():
                if coin.get("total_volume") is not None:
                    volume_map[coin["id"]] = coin["total_volume"]
        except requests.RequestException as e:
            output({"warning": f"Volume fetch failed (non-fatal): {e}"})

        total_inserted = 0
        for asset in assets:
            coingecko_id = asset["coingecko_id"]
            asset_id = asset["asset_id"]

            try:
                # CoinGecko OHLC API — returns 4h candles for days<=30
                resp = requests.get(
                    f"https://api.coingecko.com/api/v3/coins/{coingecko_id}/ohlc",
                    params={"vs_currency": "usd", "days": str(args.days)},
                    headers=cg_headers,
                    timeout=30,
                )
                resp.raise_for_status()
                candles = resp.json()

                if not isinstance(candles, list):
                    output({"warning": f"{asset['symbol']}: unexpected response from CoinGecko"})
                    continue

                # Aggregate 4h candles to daily
                from collections import defaultdict
                daily_data = defaultdict(lambda: {"open": None, "high": float("-inf"), "low": float("inf"), "close": None, "candles": 0})

                for c in candles:
                    ts = datetime.fromtimestamp(c[0] / 1000, tz=timezone.utc)
                    day_key = ts.strftime("%Y-%m-%d")
                    d = daily_data[day_key]
                    if d["open"] is None:
                        d["open"] = c[1]
                    d["high"] = max(d["high"], c[2])
                    d["low"] = min(d["low"], c[3])
                    d["close"] = c[4]
                    d["candles"] += 1

                # Attach 24h volume to yesterday's completed day (not today's partial)
                # When run at 02:00 UTC on Apr 5, the /coins/markets 24h volume
                # approximates Apr 4's full-day volume. Today's OHLC is incomplete.
                yesterday_str = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
                yesterday_volume = volume_map.get(coingecko_id)

                count = 0
                sorted_days = sorted(daily_data.items())
                today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                for day_str, d in sorted_days:
                    if d["open"] is None or d["candles"] < 2:
                        continue  # Skip incomplete days

                    # Skip today's partial candle — incomplete OHLCV
                    if day_str == today_str:
                        continue

                    # Volume: attach to yesterday only (closest to full 24h)
                    volume = Decimal(str(yesterday_volume)) if yesterday_volume and day_str == yesterday_str else None

                    if volume is not None:
                        conn.execute(
                            f"""INSERT INTO {s}.ohlcv_daily
                                (asset_id, venue_id, date, open, high, low, close, volume)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (asset_id, venue_id, date) DO UPDATE SET
                                    open = EXCLUDED.open, high = EXCLUDED.high,
                                    low = EXCLUDED.low, close = EXCLUDED.close,
                                    volume = EXCLUDED.volume""",
                            (
                                asset_id, cg_venue_id, day_str,
                                Decimal(str(d["open"])), Decimal(str(d["high"])),
                                Decimal(str(d["low"])), Decimal(str(d["close"])),
                                volume,
                            ),
                        )
                    else:
                        conn.execute(
                            f"""INSERT INTO {s}.ohlcv_daily
                                (asset_id, venue_id, date, open, high, low, close)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (asset_id, venue_id, date) DO UPDATE SET
                                    open = EXCLUDED.open, high = EXCLUDED.high,
                                    low = EXCLUDED.low, close = EXCLUDED.close""",
                            (
                                asset_id, cg_venue_id, day_str,
                                Decimal(str(d["open"])), Decimal(str(d["high"])),
                                Decimal(str(d["low"])), Decimal(str(d["close"])),
                            ),
                        )
                    count += 1

                total_inserted += count
                conn.commit()

            except requests.RequestException as e:
                output({"warning": f"{asset['symbol']}: CoinGecko API error: {e}"})
                continue

    output({"status": "ok", "assets_fetched": len(assets), "days_inserted": total_inserted, "volumes_fetched": len(volume_map)})


def cmd_compute_daily_ta(args):
    """Recompute daily TA for all assets using latest OHLCV data (last row only)."""
    import pandas as pd
    from core.indicators import compute_daily

    s = schema()
    with sync_connect() as conn:
        cur = conn.execute(
            f"SELECT id, symbol FROM {s}.assets WHERE is_active = true AND deleted_at IS NULL"
        )
        assets = cur.fetchall()

        count = 0
        for asset in assets:
            asset_id = asset["id"]

            cur = conn.execute(
                f"""SELECT date, open, high, low, close, volume
                    FROM {s}.ohlcv_daily WHERE asset_id = %s ORDER BY date ASC""",
                (asset_id,),
            )
            rows = cur.fetchall()
            if len(rows) < 15:
                continue

            df = pd.DataFrame([dict(r) for r in rows])
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            indicators = compute_daily(df)
            if indicators.empty:
                continue

            # Only write the last row (today's TA)
            latest = indicators.iloc[-1]
            date_val = df.iloc[-1]["date"]

            cols = [
                "rsi_14", "rsi_7", "stoch_rsi_k", "stoch_rsi_d",
                "ema_9", "ema_12", "ema_20", "ema_26", "ema_50", "ema_200",
                "sma_50", "sma_200",
                "macd", "macd_signal", "macd_hist",
                "atr_14", "bb_upper", "bb_lower", "bb_width",
                "adx_14",
                "obv", "volume_sma_20", "volume_ratio",
                "regime_score",
            ]
            custom_cols = ["ema_8", "kc_upper", "kc_lower", "squeeze", "high_20d"]

            values = [asset_id, date_val]
            for col in cols:
                val = latest.get(col)
                if pd.notna(val):
                    values.append(Decimal(str(round(float(val), 8))))
                else:
                    values.append(None)

            custom = {}
            for col in custom_cols:
                val = latest.get(col)
                if pd.notna(val):
                    custom[col] = round(float(val), 8)
            values.append(json.dumps(custom) if custom else "{}")

            all_cols = cols + ["custom"]
            placeholders = ", ".join(f"%s" for _ in values)
            col_names = "asset_id, date, " + ", ".join(all_cols)

            conn.execute(
                f"""INSERT INTO {s}.indicators_daily ({col_names})
                    VALUES ({placeholders})
                    ON CONFLICT (asset_id, date) DO UPDATE SET
                        {', '.join(f'{c} = EXCLUDED.{c}' for c in all_cols)}
                """,
                values,
            )
            count += 1

        conn.commit()

    output({"status": "ok", "assets_computed": count})


def cmd_fetch_sentiment(args):
    """Fetch Fear & Greed Index and store in indicators_daily.custom."""
    import requests as req

    s = schema()
    try:
        resp = req.get("https://api.alternative.me/fng/?limit=1", timeout=15)
        resp.raise_for_status()
        data = resp.json()
        fng = data["data"][0]
        fgi_value = int(fng["value"])
        fgi_class = fng["value_classification"]
    except Exception as e:
        error(f"Failed to fetch Fear & Greed Index: {e}")

    with sync_connect() as conn:
        # Update custom JSONB on all assets' latest indicators_daily row
        cur = conn.execute(
            f"SELECT DISTINCT asset_id FROM {s}.indicators_daily"
        )
        assets = cur.fetchall()

        updated = 0
        for asset in assets:
            conn.execute(
                f"""UPDATE {s}.indicators_daily
                    SET custom = COALESCE(custom, '{{}}'::jsonb) || %s::jsonb
                    WHERE id = (
                        SELECT id FROM {s}.indicators_daily
                        WHERE asset_id = %s ORDER BY date DESC LIMIT 1
                    )""",
                (json.dumps({"fear_greed_index": fgi_value, "fear_greed_class": fgi_class}), asset["asset_id"]),
            )
            updated += 1

        conn.commit()

    output({
        "status": "ok",
        "fear_greed_index": fgi_value,
        "classification": fgi_class,
        "assets_updated": updated,
    })


def cmd_sentiment(args):
    """Show current sentiment score and optionally store Robin's news score."""
    from core.sentiment import (
        load_sentiment_data, compute_sentiment_score,
        get_sentiment_adjustments, store_sentiment_snapshot, get_sentiment_trend,
    )

    s = schema()
    with sync_connect() as conn:
        # Load FGI + funding rate from DB
        data = load_sentiment_data(conn, s, "BTC")

        # Compute composite score
        score, classification = compute_sentiment_score(
            fear_greed_index=data.get("fear_greed_index"),
            funding_rate=data.get("funding_rate"),
            news_score=args.news_score,
        )

        adjustments = get_sentiment_adjustments(classification)

        # Store snapshot if news_score provided (Robin is actively scoring)
        if args.news_score is not None:
            store_sentiment_snapshot(
                conn, s, score, classification,
                data.get("fear_greed_index"), data.get("funding_rate"), args.news_score,
            )
            conn.commit()

        # Get trend
        trend = get_sentiment_trend(conn, s, days=7)

    output({
        "score": score,
        "classification": classification,
        "components": {
            "fear_greed_index": data.get("fear_greed_index"),
            "fear_greed_class": data.get("fear_greed_class"),
            "funding_rate": data.get("funding_rate"),
            "news_score": args.news_score,
        },
        "grid_adjustments": adjustments,
        "trend_7d": trend,
    })


def cmd_sync_fees(args):
    """Sync trading pair fees from exchange API."""
    from core.exchange import CcxtExchange

    s = schema()
    with sync_connect() as conn:
        # Find exchange venues
        if args.venue:
            cur = conn.execute(
                f"SELECT id, code, ccxt_id FROM {s}.venues WHERE code = %s AND type = 'exchange'",
                (args.venue,),
            )
        else:
            cur = conn.execute(
                f"SELECT id, code, ccxt_id FROM {s}.venues WHERE type = 'exchange' AND is_active = true AND deleted_at IS NULL"
            )
        venues = cur.fetchall()

        total_updated = 0
        for venue in venues:
            try:
                ex = CcxtExchange(venue["ccxt_id"] or venue["code"])
                ex.exchange.load_markets()
            except Exception as e:
                output({"warning": f"Failed to load markets for {venue['code']}: {e}"})
                continue

            cur = conn.execute(
                f"""SELECT id, pair_symbol, maker_fee, taker_fee
                    FROM {s}.trading_pairs
                    WHERE venue_id = %s AND is_active = true AND is_current = true""",
                (venue["id"],),
            )
            pairs = cur.fetchall()

            for pair in pairs:
                try:
                    market = ex.exchange.market(pair["pair_symbol"])
                except Exception:
                    continue

                new_maker = Decimal(str(market.get("maker") or 0))
                new_taker = Decimal(str(market.get("taker") or 0))

                if new_maker != pair["maker_fee"] or new_taker != pair["taker_fee"]:
                    conn.execute(
                        f"UPDATE {s}.trading_pairs SET maker_fee = %s, taker_fee = %s WHERE id = %s",
                        (new_maker, new_taker, pair["id"]),
                    )
                    total_updated += 1

            conn.commit()

    output({"status": "ok", "pairs_updated": total_updated})


def cmd_poller_status(args):
    """Read poller health status from JSON file."""
    from pathlib import Path
    status_file = Path(".poller_status.json")
    if not status_file.exists():
        status_file = Path("/opt/inotagent-trading/.poller_status.json")
    if not status_file.exists():
        error("No poller status file found")
    output(json.loads(status_file.read_text()))


def cmd_sync_coingecko(args):
    """Sync CoinGecko coin universe + blockchain platforms into ext_ tables.

    - /coins/list?include_platform=true → ext_coingecko_assets (~14k coins)
    - /asset_platforms → ext_coingecko_platforms (~90 chains)

    Run periodically (weekly) to keep the universe fresh. Safe to re-run.
    """
    import os
    import requests

    cg_api_key = os.environ.get("COINGECKO_API_KEY")
    cg_headers = {"x_cg_demo_api_key": cg_api_key} if cg_api_key else {}

    s = schema()

    # ── 1. Sync platforms (blockchains) ──
    platforms_count = 0
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/asset_platforms",
            headers=cg_headers,
            timeout=30,
        )
        resp.raise_for_status()
        platforms = resp.json()

        with sync_connect() as conn:
            for p in platforms:
                pid = p.get("id")
                if not pid:
                    continue
                conn.execute(
                    f"""INSERT INTO {s}.ext_coingecko_platforms
                        (platform_id, name, chain_identifier, native_coin_id, synced_at)
                        VALUES (%s, %s, %s, %s, NOW())
                        ON CONFLICT (platform_id) DO UPDATE SET
                            name = EXCLUDED.name,
                            chain_identifier = EXCLUDED.chain_identifier,
                            native_coin_id = EXCLUDED.native_coin_id,
                            synced_at = NOW()""",
                    (pid, p.get("name"), p.get("chain_identifier"), p.get("native_coin_id")),
                )
                platforms_count += 1
            conn.commit()
    except requests.RequestException as e:
        output({"warning": f"Platform sync failed: {e}"})

    # ── 2. Sync coins ──
    coins_count = 0
    rank_map = {}
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/coins/list",
            params={"include_platform": "true"},
            headers=cg_headers,
            timeout=60,
        )
        resp.raise_for_status()
        coins = resp.json()

        # Fetch market cap ranks in batches (coins/markets, 250 per page)
        # Only fetch top 500 to avoid rate limits — rest get rank=NULL
        rank_map = {}
        for page in range(1, 3):  # 2 pages × 250 = top 500
            try:
                resp = requests.get(
                    "https://api.coingecko.com/api/v3/coins/markets",
                    params={"vs_currency": "usd", "order": "market_cap_desc",
                            "per_page": 250, "page": page},
                    headers=cg_headers,
                    timeout=30,
                )
                resp.raise_for_status()
                for coin in resp.json():
                    rank_map[coin["id"]] = coin.get("market_cap_rank")
            except requests.RequestException:
                break  # Non-fatal — ranks are optional

        import json
        with sync_connect() as conn:
            for coin in coins:
                cg_id = coin.get("id")
                if not cg_id:
                    continue
                platforms_json = json.dumps(coin.get("platforms", {})) if coin.get("platforms") else None
                rank = rank_map.get(cg_id)

                conn.execute(
                    f"""INSERT INTO {s}.ext_coingecko_assets
                        (coingecko_id, symbol, name, platforms, market_cap_rank, synced_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (coingecko_id) DO UPDATE SET
                            symbol = EXCLUDED.symbol,
                            name = EXCLUDED.name,
                            platforms = EXCLUDED.platforms,
                            market_cap_rank = COALESCE(EXCLUDED.market_cap_rank, {s}.ext_coingecko_assets.market_cap_rank),
                            synced_at = NOW()""",
                    (cg_id, (coin.get("symbol") or "")[:32], (coin.get("name") or "")[:128], platforms_json, rank),
                )
                coins_count += 1
            conn.commit()
    except requests.RequestException as e:
        output({"warning": f"Coin sync failed: {e}"})

    output({
        "status": "ok",
        "platforms_synced": platforms_count,
        "coins_synced": coins_count,
        "top_500_ranked": len(rank_map),
    })


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

    p = sub.add_parser("fetch-daily")
    p.add_argument("--days", type=int, default=1, choices=[1, 7, 14, 30, 90, 180, 365],
                   help="Days to fetch (CoinGecko OHLC: 1/7/14/30 free, 90/180/365 paid)")

    sub.add_parser("compute-daily-ta")

    p = sub.add_parser("backfill-daily-ta")
    p.add_argument("--asset", required=True)

    sub.add_parser("fetch-sentiment")

    p = sub.add_parser("sentiment")
    p.add_argument("--news-score", type=float, default=None, help="Robin's news sentiment score (-1.0 to +1.0)")

    p = sub.add_parser("sync-fees")
    p.add_argument("--venue", default=None, help="Venue to sync (default: all exchange venues)")

    sub.add_parser("coverage")
    sub.add_parser("poller-status")
    sub.add_parser("sync-coingecko")

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
        "fetch-daily": cmd_fetch_daily,
        "compute-daily-ta": cmd_compute_daily_ta,
        "backfill-daily-ta": cmd_backfill_daily_ta,
        "fetch-sentiment": cmd_fetch_sentiment,
        "sentiment": cmd_sentiment,
        "sync-fees": cmd_sync_fees,
        "coverage": cmd_coverage,
        "poller-status": cmd_poller_status,
        "sync-coingecko": cmd_sync_coingecko,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
