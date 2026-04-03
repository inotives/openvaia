"""Public data poller — fetches 1m OHLCV + ticker for all active pairs.

No API key needed. Fast, must not fail.

Usage:
    python -m poller.public
    python -m poller.public --pairs CRO/USDT,BTC/USDT --interval 60
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal

from core.config import settings
from core.db import async_conn, close_async_pool, get_async_pool, schema
from core.exchange import CcxtExchange
from poller.base import BasePoller

logger = logging.getLogger(__name__)


class PublicPoller(BasePoller):
    name = "public"

    def __init__(self, pairs: list[str], interval: int = 60) -> None:
        super().__init__(interval=interval)
        self.pairs = pairs
        self.exchange: CcxtExchange | None = None

    async def setup(self) -> None:
        self.exchange = CcxtExchange()
        await get_async_pool()
        logger.info(f"[public] Watching pairs: {self.pairs}")

    async def cycle(self) -> None:
        """Fetch 1m candles + ticker for each pair, store to ohlcv_1m."""
        s = schema()
        now = datetime.now(timezone.utc)

        for pair in self.pairs:
            try:
                # Fetch ticker (bid, ask, spread, volume_24h)
                ticker = self.exchange.fetch_ticker(pair)

                # Fetch latest 1m candle
                candles = self.exchange.fetch_ohlcv(pair, "1m", limit=1)
                if not candles:
                    logger.warning(f"[public] No candles for {pair}")
                    continue

                candle = candles[-1]  # [timestamp, open, high, low, close, volume]

                # Resolve asset_id and venue_id
                base_symbol = pair.split("/")[0]

                bid = ticker.get("bid")
                ask = ticker.get("ask")
                spread_pct = None
                if bid and ask:
                    mid = (bid + ask) / 2
                    if mid > 0:
                        spread_pct = (ask - bid) / mid * 100

                async with async_conn() as conn:
                    # Look up asset_id
                    row = await conn.fetchrow(
                        f"SELECT id FROM {s}.assets WHERE symbol = $1 AND deleted_at IS NULL",
                        base_symbol,
                    )
                    if not row:
                        logger.warning(f"[public] Asset {base_symbol} not found in DB, skipping")
                        continue
                    asset_id = row["id"]

                    # Look up venue_id
                    venue_row = await conn.fetchrow(
                        f"SELECT id FROM {s}.venues WHERE code = $1 AND deleted_at IS NULL",
                        self.exchange.exchange_id,
                    )
                    if not venue_row:
                        logger.warning(f"[public] Venue {self.exchange.exchange_id} not found in DB")
                        continue
                    venue_id = venue_row["id"]

                    # Upsert ohlcv_1m
                    ts = datetime.fromtimestamp(candle[0] / 1000, tz=timezone.utc)
                    await conn.execute(
                        f"""INSERT INTO {s}.ohlcv_1m
                            (asset_id, venue_id, timestamp, open, high, low, close, volume,
                             bid, ask, spread_pct, volume_24h)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                            ON CONFLICT (asset_id, venue_id, timestamp) DO UPDATE SET
                                open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
                                close = EXCLUDED.close, volume = EXCLUDED.volume,
                                bid = EXCLUDED.bid, ask = EXCLUDED.ask,
                                spread_pct = EXCLUDED.spread_pct, volume_24h = EXCLUDED.volume_24h
                        """,
                        asset_id, venue_id, ts,
                        Decimal(str(candle[1])), Decimal(str(candle[2])),
                        Decimal(str(candle[3])), Decimal(str(candle[4])),
                        Decimal(str(candle[5])),
                        Decimal(str(bid)) if bid else None,
                        Decimal(str(ask)) if ask else None,
                        Decimal(str(spread_pct)) if spread_pct else None,
                        Decimal(str(ticker.get("quoteVolume", 0))),
                    )

                logger.debug(f"[public] {pair} @ {candle[4]:.6f} bid={bid} ask={ask}")

            except Exception as e:
                logger.error(f"[public] Failed to fetch {pair}: {e}")
                raise  # Let base poller handle retry

    async def teardown(self) -> None:
        await close_async_pool()


def main():
    parser = argparse.ArgumentParser(description="Public data poller")
    parser.add_argument("--pairs", default=settings.public_poller_pairs, help="Comma-separated pairs")
    parser.add_argument("--interval", type=int, default=settings.public_poller_interval)
    args = parser.parse_args()

    pairs = [p.strip() for p in args.pairs.split(",") if p.strip()]

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    poller = PublicPoller(pairs=pairs, interval=args.interval)
    asyncio.run(poller.run())


if __name__ == "__main__":
    main()
