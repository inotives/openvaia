"""Public data poller — fetches 1m OHLCV + ticker for all active trading pairs.

No API key needed. Loads pairs from DB (trading_pairs table), not env vars.
Handles exchange differences via ccxt normalization + defensive conversion.

Usage:
    python -m poller.public
    python -m poller.public --interval 60
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from core.config import settings
from core.db import async_conn, close_async_pool, get_async_pool, schema
from core.exchange import CcxtExchange
from poller.base import BasePoller

logger = logging.getLogger(__name__)


def _to_decimal(value) -> Decimal | None:
    """Safely convert any value to Decimal. Returns None on failure."""
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


class PublicPoller(BasePoller):
    name = "public"

    def __init__(self, interval: int = 60) -> None:
        super().__init__(interval=interval)
        self.exchange: CcxtExchange | None = None
        self._pair_cache: list[dict] | None = None  # cached from DB

    async def setup(self) -> None:
        self.exchange = CcxtExchange()
        await get_async_pool()

    async def _load_pairs(self) -> list[dict]:
        """Load active trading pairs from DB. Cached, refreshed every cycle."""
        s = schema()
        async with async_conn() as conn:
            # Find venue_id for this exchange
            venue_row = await conn.fetchrow(
                f"SELECT id FROM {s}.venues WHERE code = $1 AND deleted_at IS NULL",
                self.exchange.exchange_id,
            )
            if not venue_row:
                logger.warning(f"[public] Venue {self.exchange.exchange_id} not found in DB")
                return []

            venue_id = venue_row["id"]

            # Load active trading pairs for this venue
            rows = await conn.fetch(
                f"""SELECT tp.pair_symbol, tp.base_asset_id, a.symbol AS base_symbol
                    FROM {s}.trading_pairs tp
                    JOIN {s}.assets a ON a.id = tp.base_asset_id
                    WHERE tp.venue_id = $1 AND tp.is_active = true AND tp.is_current = true""",
                venue_id,
            )

            pairs = [
                {
                    "pair_symbol": r["pair_symbol"],  # ccxt format: CRO/USDT
                    "asset_id": r["base_asset_id"],
                    "venue_id": venue_id,
                }
                for r in rows
            ]

            if pairs:
                logger.info(f"[public] Loaded {len(pairs)} pairs from DB: {[p['pair_symbol'] for p in pairs]}")
            else:
                logger.warning(f"[public] No active trading pairs found for {self.exchange.exchange_id}")

            return pairs

    async def cycle(self) -> None:
        """Fetch 1m candles + ticker for each pair, store to ohlcv_1m."""
        s = schema()

        # Refresh pair list from DB each cycle
        self._pair_cache = await self._load_pairs()
        if not self._pair_cache:
            return

        for pair_info in self._pair_cache:
            pair_symbol = pair_info["pair_symbol"]
            asset_id = pair_info["asset_id"]
            venue_id = pair_info["venue_id"]

            try:
                # Fetch ticker — ccxt normalizes across exchanges
                # Returns: {bid, ask, last, high, low, baseVolume, quoteVolume, ...}
                ticker = self.exchange.fetch_ticker(pair_symbol)

                # Fetch latest 1m candle — ccxt normalizes to [timestamp, O, H, L, C, V]
                candles = self.exchange.fetch_ohlcv(pair_symbol, "1m", limit=1)
                if not candles:
                    logger.warning(f"[public] No candles for {pair_symbol}")
                    continue

                candle = candles[-1]

                # Extract ticker fields (may be None on some exchanges)
                bid = ticker.get("bid")
                ask = ticker.get("ask")

                # Compute spread (defensive — bid/ask may be None)
                spread_pct = None
                if bid is not None and ask is not None and bid > 0 and ask > 0:
                    mid = (bid + ask) / 2
                    if mid > 0:
                        spread_pct = (ask - bid) / mid * 100

                # 24h volume: try quoteVolume first, fallback to baseVolume
                volume_24h = ticker.get("quoteVolume") or ticker.get("baseVolume")

                # Write to DB — all values go through _to_decimal for safety
                ts = datetime.fromtimestamp(candle[0] / 1000, tz=timezone.utc)

                async with async_conn() as conn:
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
                        _to_decimal(candle[1]),  # open
                        _to_decimal(candle[2]),  # high
                        _to_decimal(candle[3]),  # low
                        _to_decimal(candle[4]),  # close
                        _to_decimal(candle[5]),  # volume
                        _to_decimal(bid),
                        _to_decimal(ask),
                        _to_decimal(spread_pct),
                        _to_decimal(volume_24h) or Decimal("0"),
                    )

                logger.debug(
                    f"[public] {pair_symbol} @ {candle[4]} bid={bid} ask={ask}"
                )

            except Exception as e:
                logger.error(f"[public] Failed to fetch {pair_symbol}: {e}")
                raise  # Let base poller handle retry

    async def teardown(self) -> None:
        await close_async_pool()


def main():
    parser = argparse.ArgumentParser(description="Public data poller")
    parser.add_argument("--interval", type=int, default=settings.public_poller_interval)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    poller = PublicPoller(interval=args.interval)
    asyncio.run(poller.run())


if __name__ == "__main__":
    main()
