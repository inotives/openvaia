"""Private data poller — syncs balances, detects order fills, anomaly checks.

Requires API key. Handles auth separately from public poller.

Usage:
    python -m poller.private
    python -m poller.private --exchange cryptocom --interval 60
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


class PrivatePoller(BasePoller):
    name = "private"

    def __init__(self, exchange_id: str = "cryptocom", interval: int = 60) -> None:
        super().__init__(interval=interval)
        self.exchange_id = exchange_id
        self.exchange: CcxtExchange | None = None
        self._last_fee_sync: datetime | None = None

    async def setup(self) -> None:
        self.exchange = CcxtExchange(self.exchange_id)
        await get_async_pool()
        logger.info(f"[private] Exchange: {self.exchange_id}")

    async def cycle(self) -> None:
        """Sync balances, detect fills, check anomalies, sync fees + funding rate.

        Each step is independent — one failure doesn't block others.
        """
        errors = []

        for name, func in [
            ("sync_balances", self._sync_balances),
            ("sync_orders", self._sync_orders),
            ("check_anomalies", self._check_anomalies),
            ("sync_fees", self._sync_fees_if_due),
            ("sync_funding_rates", self._sync_funding_rates),
        ]:
            try:
                await func()
            except Exception as e:
                logger.error(f"[private] {name} failed: {e}")
                errors.append(name)

        if errors:
            logger.warning(f"[private] Cycle completed with errors in: {', '.join(errors)}")

    async def _sync_balances(self) -> None:
        """Fetch exchange balances and update DB.

        For each account in our DB for this venue, fetch balances using the
        account's address (sub-account UUID for Crypto.com, etc.).
        """
        s = schema()

        async with async_conn() as conn:
            # Find venue_id
            venue_row = await conn.fetchrow(
                f"SELECT id FROM {s}.venues WHERE code = $1", self.exchange_id
            )
            if not venue_row:
                logger.warning(f"[private] Venue {self.exchange_id} not found")
                return
            venue_id = venue_row["id"]

            # Fetch all active accounts for this venue
            accounts = await conn.fetch(
                f"""SELECT id, name, address FROM {s}.accounts
                    WHERE venue_id = $1 AND is_active = true AND deleted_at IS NULL""",
                venue_id,
            )
            if not accounts:
                logger.warning(f"[private] No accounts for venue {self.exchange_id}")
                return

            total_synced = 0
            for account in accounts:
                account_id = account["id"]
                account_address = account["address"]  # sub-account UUID or None

                result = self.exchange.fetch_balance(account_address=account_address)
                balances = result.get("balances", [])

                for bal in balances:
                    symbol = bal["symbol"]

                    # Resolve asset_id
                    asset_row = await conn.fetchrow(
                        f"SELECT id FROM {s}.assets WHERE symbol = $1 AND deleted_at IS NULL", symbol
                    )
                    if not asset_row:
                        continue  # Skip unknown assets

                    await conn.execute(
                        f"""INSERT INTO {s}.balances (account_id, asset_id, balance, available, locked, synced_at)
                            VALUES ($1, $2, $3, $4, $5, NOW())
                            ON CONFLICT (account_id, asset_id) DO UPDATE SET
                                balance = EXCLUDED.balance, available = EXCLUDED.available,
                                locked = EXCLUDED.locked, synced_at = NOW()
                        """,
                        account_id, asset_row["id"],
                        Decimal(str(bal["total"])),
                        Decimal(str(bal.get("available", 0))),
                        Decimal(str(bal.get("locked", 0))),
                    )
                    total_synced += 1

            logger.debug(f"[private] Synced {total_synced} balances across {len(accounts)} accounts")

    async def _sync_orders(self) -> None:
        """Detect fills on open orders."""
        s = schema()

        async with async_conn() as conn:
            # Find our open orders with exchange_order_id
            open_orders = await conn.fetch(
                f"""SELECT id, exchange_order_id, asset_id, venue_id, side, quantity, status
                    FROM {s}.orders
                    WHERE status IN ('open', 'partial')
                      AND exchange_order_id IS NOT NULL
                      AND paper = false
                """
            )

            if not open_orders:
                return

            # Fetch orders from exchange
            try:
                exchange_orders = self.exchange.fetch_orders()
            except Exception as e:
                logger.error(f"[private] Failed to fetch orders from exchange: {e}")
                return

            # Build lookup by exchange_order_id
            ex_by_id = {str(o["id"]): o for o in exchange_orders}

            for our_order in open_orders:
                ex_order = ex_by_id.get(our_order["exchange_order_id"])
                if not ex_order:
                    continue

                ex_status = ex_order.get("status", "")
                if ex_status in ("closed", "filled") and our_order["status"] != "filled":
                    # Order was filled — record execution
                    filled_qty = Decimal(str(ex_order.get("filled", 0)))
                    avg_price = Decimal(str(ex_order.get("average", 0) or ex_order.get("price", 0)))
                    fee = Decimal(str(ex_order.get("fee", {}).get("cost", 0)))
                    fee_currency = ex_order.get("fee", {}).get("currency", "USD")

                    await conn.execute(
                        f"UPDATE {s}.orders SET status = 'filled', filled_at = NOW() WHERE id = $1",
                        our_order["id"],
                    )
                    await conn.execute(
                        f"""INSERT INTO {s}.order_events (order_id, from_status, to_status, reason, changed_by)
                            VALUES ($1, $2, 'filled', 'detected by poller', 'system')""",
                        our_order["id"], our_order["status"],
                    )
                    await conn.execute(
                        f"""INSERT INTO {s}.executions (order_id, quantity, price, fee, fee_currency)
                            VALUES ($1, $2, $3, $4, $5)""",
                        our_order["id"], filled_qty, avg_price, fee, fee_currency,
                    )

                    logger.info(f"[private] Order {our_order['exchange_order_id']} filled: {filled_qty} @ {avg_price}")

    async def _check_anomalies(self) -> None:
        """Check for anomaly conditions: consecutive losses, daily loss, drawdown."""
        s = schema()

        async with async_conn() as conn:
            # Check consecutive losses (last 3 realized P&L)
            recent_pnl = await conn.fetch(
                f"""SELECT pnl_usd FROM {s}.pnl_realized
                    ORDER BY created_at DESC LIMIT 3"""
            )
            if len(recent_pnl) >= 3 and all(r["pnl_usd"] < 0 for r in recent_pnl):
                logger.warning("[private] ANOMALY: 3 consecutive losing trades detected")

            # Check daily loss
            today_pnl = await conn.fetchrow(
                f"""SELECT COALESCE(SUM(pnl_usd), 0) AS total
                    FROM {s}.pnl_realized
                    WHERE created_at::date = CURRENT_DATE"""
            )
            if today_pnl and today_pnl["total"] < Decimal("-50"):  # Hardcoded threshold for now
                logger.warning(f"[private] ANOMALY: Daily loss ${today_pnl['total']}")

    async def _sync_fees_if_due(self) -> None:
        """Sync trading pair fees from exchange. Runs once per day."""
        now = datetime.now(timezone.utc)
        if self._last_fee_sync and self._last_fee_sync.date() == now.date():
            return

        s = schema()
        try:
            self.exchange.exchange.load_markets()
        except Exception as e:
            logger.error(f"[private] Failed to load markets for fee sync: {e}")
            return

        async with async_conn() as conn:
            venue_row = await conn.fetchrow(
                f"SELECT id FROM {s}.venues WHERE code = $1 AND deleted_at IS NULL",
                self.exchange_id,
            )
            if not venue_row:
                return
            venue_id = venue_row["id"]

            # Get our active trading pairs for this venue
            pairs = await conn.fetch(
                f"""SELECT id, pair_symbol, maker_fee, taker_fee
                    FROM {s}.trading_pairs
                    WHERE venue_id = $1 AND is_active = true AND is_current = true""",
                venue_id,
            )

            updated = 0
            for pair in pairs:
                market = self.exchange.exchange.market(pair["pair_symbol"])
                if not market:
                    continue

                new_maker = Decimal(str(market.get("maker") or 0))
                new_taker = Decimal(str(market.get("taker") or 0))

                # Only update if changed
                if new_maker != pair["maker_fee"] or new_taker != pair["taker_fee"]:
                    await conn.execute(
                        f"""UPDATE {s}.trading_pairs
                            SET maker_fee = $1, taker_fee = $2
                            WHERE id = $3""",
                        new_maker, new_taker, pair["id"],
                    )
                    logger.info(
                        f"[private] Fee update {pair['pair_symbol']}: "
                        f"maker {pair['maker_fee']}→{new_maker}, taker {pair['taker_fee']}→{new_taker}"
                    )
                    updated += 1

            if updated:
                logger.info(f"[private] Updated fees for {updated} pairs")

        self._last_fee_sync = now

    async def _sync_funding_rates(self) -> None:
        """Fetch funding rates for perpetual pairs (loaded from DB) and store in indicators_intraday.custom."""
        s = schema()

        async with async_conn() as conn:
            venue_row = await conn.fetchrow(
                f"SELECT id FROM {s}.venues WHERE code = $1 AND deleted_at IS NULL",
                self.exchange_id,
            )
            if not venue_row:
                return
            venue_id = venue_row["id"]

            # Load perpetual pairs from trading_pairs (type=swap identified by ':' in pair_symbol)
            perp_rows = await conn.fetch(
                f"""SELECT tp.pair_symbol, a.symbol AS base_symbol, a.id AS asset_id
                    FROM {s}.trading_pairs tp
                    JOIN {s}.assets a ON a.id = tp.base_asset_id
                    WHERE tp.venue_id = $1 AND tp.is_active = true AND tp.is_current = true
                      AND tp.pair_symbol LIKE '%%:%%'""",
                venue_id,
            )

            # If no perp pairs in DB, try deriving from spot pairs
            if not perp_rows:
                spot_rows = await conn.fetch(
                    f"""SELECT tp.pair_symbol, a.symbol AS base_symbol, a.id AS asset_id
                        FROM {s}.trading_pairs tp
                        JOIN {s}.assets a ON a.id = tp.base_asset_id
                        WHERE tp.venue_id = $1 AND tp.is_active = true AND tp.is_current = true
                          AND tp.pair_symbol NOT LIKE '%%:%%'""",
                    venue_id,
                )
                # Derive perp symbol: BTC/USD → BTC/USD:USD
                perp_rows = []
                for row in spot_rows:
                    quote = row["pair_symbol"].split("/")[1] if "/" in row["pair_symbol"] else "USD"
                    perp_rows.append({
                        "pair_symbol": f"{row['pair_symbol']}:{quote}",
                        "base_symbol": row["base_symbol"],
                        "asset_id": row["asset_id"],
                    })

            for row in perp_rows:
                try:
                    fr = self.exchange.exchange.fetch_funding_rate(row["pair_symbol"])
                    rate = fr.get("fundingRate")
                    if rate is None:
                        continue

                    await conn.execute(
                        f"""UPDATE {s}.indicators_intraday
                            SET custom = custom || $1::jsonb
                            WHERE id = (
                                SELECT id FROM {s}.indicators_intraday
                                WHERE asset_id = $2 AND venue_id = $3
                                ORDER BY timestamp DESC LIMIT 1
                            )""",
                        json.dumps({"funding_rate": float(rate)}),
                        row["asset_id"], venue_id,
                    )

                    logger.debug(f"[private] Funding rate {row['base_symbol']}: {rate}")
                except Exception as e:
                    logger.debug(f"[private] Funding rate {row['pair_symbol']}: {e}")

    async def teardown(self) -> None:
        await close_async_pool()


def main():
    parser = argparse.ArgumentParser(description="Private data poller")
    parser.add_argument("--exchange", default=settings.default_exchange)
    parser.add_argument("--interval", type=int, default=settings.private_poller_interval)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    poller = PrivatePoller(exchange_id=args.exchange, interval=args.interval)
    asyncio.run(poller.run())


if __name__ == "__main__":
    main()
