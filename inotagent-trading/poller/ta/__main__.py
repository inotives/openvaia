"""TA compute poller — computes technical analysis from DB data only.

No exchange calls. Reads ohlcv_1m and ohlcv_daily, writes indicators.
Also handles: paper stop-loss monitoring, ohlcv_1m archival/pruning.

Usage:
    python -m poller.ta
    python -m poller.ta --interval 60
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pandas as pd

from core.config import settings
from core.db import async_conn, close_async_pool, get_async_pool, schema
from core.indicators import compute_daily, compute_intraday
from poller.base import BasePoller

logger = logging.getLogger(__name__)


class TAPoller(BasePoller):
    name = "ta"

    def __init__(self, interval: int = 60) -> None:
        super().__init__(interval=interval)
        self._last_daily_compute: datetime | None = None
        self._last_prune: datetime | None = None

    async def setup(self) -> None:
        await get_async_pool()

    async def cycle(self) -> None:
        """Compute intraday TA, daily TA (once/day), monitor grid, prune old data.

        Each step is independent — one failure doesn't block others.
        Grid monitoring must run even if TA computation fails.
        """
        errors = []

        for name, func in [
            ("intraday_ta", self._compute_intraday),
            ("daily_ta", self._compute_daily_if_due),
            ("paper_stop_loss", self._check_paper_stop_losses),
            ("grid_monitor", self._monitor_grid_cycles),
            ("prune", self._prune_if_due),
        ]:
            try:
                await func()
            except Exception as e:
                logger.error(f"[ta] {name} failed: {e}")
                errors.append(name)

        if errors:
            logger.warning(f"[ta] Cycle completed with errors in: {', '.join(errors)}")

    async def _compute_intraday(self) -> None:
        """Compute intraday TA from latest 1m candles for each asset/venue."""
        s = schema()

        async with async_conn() as conn:
            # Get distinct asset/venue pairs with recent data
            pairs = await conn.fetch(
                f"""SELECT DISTINCT asset_id, venue_id FROM {s}.ohlcv_1m
                    WHERE timestamp > NOW() - INTERVAL '2 hours'"""
            )

            for pair in pairs:
                asset_id, venue_id = pair["asset_id"], pair["venue_id"]

                # Fetch last 120 candles (2 hours of 1m data)
                rows = await conn.fetch(
                    f"""SELECT timestamp, open, high, low, close, volume, bid, ask
                        FROM {s}.ohlcv_1m
                        WHERE asset_id = $1 AND venue_id = $2
                        ORDER BY timestamp DESC LIMIT 120""",
                    asset_id, venue_id,
                )

                if len(rows) < 15:
                    continue

                df = pd.DataFrame([dict(r) for r in rows])
                df = df.sort_values("timestamp")
                for col in ["open", "high", "low", "close", "volume", "bid", "ask"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce")

                indicators = compute_intraday(df)
                if indicators.empty:
                    continue

                # Take the latest row
                latest = indicators.iloc[-1]
                ts = df.iloc[-1]["timestamp"]

                cols = [
                    "rsi_14", "rsi_7", "stoch_rsi_k", "stoch_rsi_d",
                    "ema_9", "ema_21", "ema_55",
                    "vwap", "volume_ratio", "obv",
                    "spread_pct", "volatility_1h", "atr_14",
                ]

                values = [asset_id, venue_id, ts]
                for col in cols:
                    val = latest.get(col)
                    if pd.notna(val):
                        values.append(Decimal(str(round(float(val), 8))))
                    else:
                        values.append(None)

                placeholders = ", ".join(f"${i}" for i in range(1, len(values) + 1))
                col_names = "asset_id, venue_id, timestamp, " + ", ".join(cols)

                await conn.execute(
                    f"""INSERT INTO {s}.indicators_intraday ({col_names})
                        VALUES ({placeholders})
                        ON CONFLICT (asset_id, venue_id, timestamp) DO UPDATE SET
                            {', '.join(f'{c} = EXCLUDED.{c}' for c in cols)},
                            computed_at = NOW()
                    """,
                    *values,
                )

            logger.debug(f"[ta] Computed intraday TA for {len(pairs)} pairs")

    async def _compute_daily_if_due(self) -> None:
        """Compute daily TA once per day (at configured UTC hour)."""
        now = datetime.now(timezone.utc)

        if self._last_daily_compute and self._last_daily_compute.date() == now.date():
            return  # Already computed today

        if now.hour < settings.ta_daily_hour:
            return  # Not time yet

        s = schema()

        async with async_conn() as conn:
            # Get assets with daily data
            assets = await conn.fetch(
                f"SELECT DISTINCT asset_id FROM {s}.ohlcv_daily"
            )

            for asset in assets:
                asset_id = asset["asset_id"]

                rows = await conn.fetch(
                    f"""SELECT date, open, high, low, close, volume
                        FROM {s}.ohlcv_daily
                        WHERE asset_id = $1
                        ORDER BY date ASC""",
                    asset_id,
                )

                if len(rows) < 15:
                    continue

                df = pd.DataFrame([dict(r) for r in rows])
                for col in ["open", "high", "low", "close", "volume"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

                indicators = compute_daily(df)
                if indicators.empty:
                    continue

                # Take the latest row
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

                values = [asset_id, date_val]
                for col in cols:
                    val = latest.get(col)
                    if pd.notna(val):
                        values.append(Decimal(str(round(float(val), 8))))
                    else:
                        values.append(None)

                placeholders = ", ".join(f"${i}" for i in range(1, len(values) + 1))
                col_names = "asset_id, date, " + ", ".join(cols)

                await conn.execute(
                    f"""INSERT INTO {s}.indicators_daily ({col_names})
                        VALUES ({placeholders})
                        ON CONFLICT (asset_id, date) DO UPDATE SET
                            {', '.join(f'{c} = EXCLUDED.{c}' for c in cols)}
                    """,
                    *values,
                )

            logger.info(f"[ta] Computed daily TA for {len(assets)} assets")
            self._last_daily_compute = now

    async def _check_paper_stop_losses(self) -> None:
        """Monitor paper orders for stop-loss triggers using latest ohlcv_1m low."""
        s = schema()

        async with async_conn() as conn:
            # Find open paper buy orders with stop_loss set
            paper_orders = await conn.fetch(
                f"""SELECT o.id, o.asset_id, o.venue_id, o.stop_loss, o.quantity
                    FROM {s}.orders o
                    WHERE o.paper = true AND o.status = 'filled' AND o.side = 'buy'
                      AND o.stop_loss IS NOT NULL
                """
            )

            for order in paper_orders:
                # Check if there's an open position (net qty > 0)
                # and if latest low breached stop-loss
                latest = await conn.fetchrow(
                    f"""SELECT low, bid FROM {s}.ohlcv_1m
                        WHERE asset_id = $1 AND venue_id = $2
                        ORDER BY timestamp DESC LIMIT 1""",
                    order["asset_id"], order["venue_id"],
                )

                if not latest:
                    continue

                low = latest["low"]
                if low is not None and low <= order["stop_loss"]:
                    fill_price = latest["bid"] or order["stop_loss"]
                    logger.warning(
                        f"[ta] Paper stop-loss triggered: order {order['id']}, "
                        f"stop={order['stop_loss']}, low={low}, fill={fill_price}"
                    )
                    # Create a sell order to close the position
                    await conn.execute(
                        f"""INSERT INTO {s}.orders
                            (asset_id, venue_id, side, type, quantity, price, status, paper,
                             created_by, rationale)
                            VALUES ($1, $2, 'sell', 'market', $3, $4, 'filled', true,
                                    'system', 'paper stop-loss triggered')""",
                        order["asset_id"], order["venue_id"],
                        order["quantity"], fill_price,
                    )
                    # Mark original order stop_loss as triggered by nullifying it
                    await conn.execute(
                        f"UPDATE {s}.orders SET stop_loss = NULL WHERE id = $1",
                        order["id"],
                    )

    async def _monitor_grid_cycles(self) -> None:
        """Monitor active DCA grid cycles — detect fills, place TPs, check stop-loss, expiry.

        Runs every poller cycle (60s). No LLM needed — purely mechanical.
        When an event is detected (fill, TP hit, stop triggered), logs it.
        Robin handles decisions (new cycles, regime transitions) via hourly task.
        """
        s = schema()
        import json as _json

        async with async_conn() as conn:
            # Load active grid cycles
            rows = await conn.fetch(
                f"""SELECT id, rationale, asset_id FROM {s}.orders
                    WHERE rationale LIKE 'grid_cycle:%%' AND status = 'open'"""
            )

            if not rows:
                return

            for row in rows:
                try:
                    cycle_data = _json.loads(row["rationale"].replace("grid_cycle:", "", 1))
                except (_json.JSONDecodeError, AttributeError):
                    continue

                cycle_id = cycle_data.get("cycle_id", "?")
                asset = cycle_data.get("asset", "?")
                mode = cycle_data.get("mode", "batch")
                levels = cycle_data.get("levels", [])
                status = cycle_data.get("status", "active")
                db_order_id = row["id"]
                changed = False

                if status not in ("active", "transition_pending", "expired_pending"):
                    continue

                # Get current price
                price_row = await conn.fetchrow(
                    f"""SELECT close FROM {s}.ohlcv_1m
                        WHERE asset_id = $1 ORDER BY timestamp DESC LIMIT 1""",
                    row["asset_id"],
                )
                if not price_row:
                    price_row = await conn.fetchrow(
                        f"""SELECT close FROM {s}.ohlcv_daily
                            WHERE asset_id = $1 ORDER BY date DESC LIMIT 1""",
                        row["asset_id"],
                    )
                if not price_row:
                    continue

                current_price = Decimal(str(price_row["close"]))

                # ── Check fills (paper mode) ──
                if status == "active":
                    for level in levels:
                        if level["status"] != "open":
                            continue
                        if current_price <= Decimal(str(level["price"])):
                            level["status"] = "filled"
                            level["quantity"] = float(Decimal(str(level["capital"])) / Decimal(str(level["price"])))

                            if level.get("buy_order_id"):
                                await conn.execute(
                                    f"UPDATE {s}.orders SET status = 'filled', filled_at = NOW() WHERE id = $1",
                                    level["buy_order_id"],
                                )

                            logger.info(f"[ta] Grid {cycle_id}: level {level['level']} filled at {level['price']}")
                            changed = True

                            # FIFO: place per-level TP
                            if mode == "adaptive_fifo":
                                profit_target = 1.5  # default, could read from strategy params
                                maker_fee = Decimal("0.0024")
                                tp_price = Decimal(str(level["price"])) * (1 + Decimal(str(profit_target / 100)) + maker_fee)
                                level["tp_price"] = float(tp_price.quantize(Decimal("0.00000001")))

                                asset_row = await conn.fetchrow(
                                    f"SELECT id FROM {s}.assets WHERE symbol = $1", asset
                                )
                                venue_row = await conn.fetchrow(
                                    f"SELECT id FROM {s}.venues WHERE code = $1", cycle_data.get("venue", "cryptocom")
                                )
                                if asset_row and venue_row:
                                    tp_row = await conn.fetchrow(
                                        f"""INSERT INTO {s}.orders
                                            (asset_id, venue_id, side, type, quantity, price, status, paper, rationale, created_by)
                                            VALUES ($1, $2, 'sell', 'limit', $3, $4, 'open', true, $5, 'grid')
                                            RETURNING id""",
                                        asset_row["id"], venue_row["id"],
                                        Decimal(str(level["quantity"])),
                                        tp_price.quantize(Decimal("0.00000001")),
                                        f"grid:{cycle_id}:tp:{level['level']}",
                                    )
                                    level["sell_order_id"] = tp_row["id"]

                    # Batch mode: update single TP
                    if mode == "batch":
                        filled = [l for l in levels if l["status"] == "filled"]
                        if filled:
                            total_cost = sum(Decimal(str(l["capital"])) for l in filled)
                            total_qty = sum(Decimal(str(l["quantity"])) for l in filled)
                            if total_qty > 0:
                                avg = total_cost / total_qty
                                profit_target = 1.5
                                maker_fee = Decimal("0.0024")
                                tp = avg * (1 + Decimal(str(profit_target / 100)) + maker_fee)
                                cycle_data["avg_entry"] = float(avg)
                                cycle_data["take_profit_price"] = float(tp.quantize(Decimal("0.00000001")))

                # ── Check TP fills (paper mode) ──
                if mode == "adaptive_fifo":
                    for level in levels:
                        if level["status"] == "filled" and level.get("tp_price") and level.get("sell_order_id"):
                            if current_price >= Decimal(str(level["tp_price"])):
                                level["status"] = "sold"
                                await conn.execute(
                                    f"UPDATE {s}.orders SET status = 'filled', filled_at = NOW() WHERE id = $1",
                                    level["sell_order_id"],
                                )
                                logger.info(f"[ta] Grid {cycle_id}: level {level['level']} TP filled at {level['tp_price']}")
                                changed = True

                    # All filled levels sold → cycle complete
                    filled_or_sold = [l for l in levels if l["status"] in ("filled", "sold")]
                    if filled_or_sold and all(l["status"] == "sold" for l in filled_or_sold):
                        for level in levels:
                            if level["status"] == "open":
                                level["status"] = "cancelled"
                                if level.get("buy_order_id"):
                                    await conn.execute(
                                        f"UPDATE {s}.orders SET status = 'cancelled' WHERE id = $1",
                                        level["buy_order_id"],
                                    )
                        cycle_data["status"] = "closed"
                        cycle_data["close_reason"] = "all_tps_filled"
                        logger.info(f"[ta] Grid {cycle_id}: cycle closed — all TPs filled")
                        changed = True

                elif mode == "batch" and cycle_data.get("take_profit_price"):
                    if current_price >= Decimal(str(cycle_data["take_profit_price"])):
                        for level in levels:
                            if level["status"] == "filled":
                                level["status"] = "sold"
                            elif level["status"] == "open":
                                level["status"] = "cancelled"
                                if level.get("buy_order_id"):
                                    await conn.execute(
                                        f"UPDATE {s}.orders SET status = 'cancelled' WHERE id = $1",
                                        level["buy_order_id"],
                                    )
                        cycle_data["status"] = "closed"
                        cycle_data["close_reason"] = "batch_tp_filled"
                        logger.info(f"[ta] Grid {cycle_id}: cycle closed — batch TP filled")
                        changed = True

                # ── Check stop-loss ──
                stop_price = cycle_data.get("stop_loss_price")
                if stop_price and current_price <= Decimal(str(stop_price)):
                    for level in levels:
                        if level["status"] in ("open", "filled"):
                            prev = level["status"]
                            level["status"] = "cancelled" if prev == "open" else "stopped"
                            oid = level.get("buy_order_id") if prev == "open" else level.get("sell_order_id")
                            if oid:
                                await conn.execute(
                                    f"UPDATE {s}.orders SET status = 'cancelled' WHERE id = $1", oid
                                )
                    cycle_data["status"] = "closed"
                    cycle_data["close_reason"] = "stop_loss"
                    logger.warning(f"[ta] Grid {cycle_id}: STOP LOSS triggered at {current_price}")
                    changed = True

                # ── Check expiry (72h) ──
                opened_at = cycle_data.get("opened_at", "")
                if opened_at and status == "active":
                    try:
                        opened = datetime.fromisoformat(opened_at)
                        hours_open = (datetime.now(timezone.utc) - opened).total_seconds() / 3600
                        if hours_open >= 72:
                            for level in levels:
                                if level["status"] == "open":
                                    level["status"] = "cancelled"
                                    if level.get("buy_order_id"):
                                        await conn.execute(
                                            f"UPDATE {s}.orders SET status = 'cancelled' WHERE id = $1",
                                            level["buy_order_id"],
                                        )
                            cycle_data["status"] = "expired_pending"
                            logger.info(f"[ta] Grid {cycle_id}: expired after {hours_open:.0f}h")
                            changed = True
                    except (ValueError, TypeError):
                        pass

                # Save updated state
                if changed:
                    cycle_json = _json.dumps(cycle_data)
                    db_status = "open" if cycle_data.get("status") == "active" else "filled"
                    await conn.execute(
                        f"UPDATE {s}.orders SET rationale = $1, status = $2 WHERE id = $3",
                        f"grid_cycle:{cycle_json}", db_status, db_order_id,
                    )

    async def _prune_if_due(self) -> None:
        """Prune ohlcv_1m older than retention period. Runs once per day."""
        now = datetime.now(timezone.utc)

        if self._last_prune and self._last_prune.date() == now.date():
            return

        s = schema()
        cutoff = now - timedelta(days=settings.ohlcv_1m_retention_days)

        async with async_conn() as conn:
            result = await conn.execute(
                f"DELETE FROM {s}.ohlcv_1m WHERE timestamp < $1", cutoff
            )
            logger.info(f"[ta] Pruned ohlcv_1m older than {cutoff.date()}: {result}")

        self._last_prune = now

    async def teardown(self) -> None:
        await close_async_pool()


def main():
    parser = argparse.ArgumentParser(description="TA compute poller")
    parser.add_argument("--interval", type=int, default=settings.ta_poller_interval)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    poller = TAPoller(interval=args.interval)
    asyncio.run(poller.run())


if __name__ == "__main__":
    main()
