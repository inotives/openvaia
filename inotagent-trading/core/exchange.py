"""Exchange wrapper — ccxt for live, paper engine for simulated trades.

Usage:
    exchange = get_exchange(paper_mode=True)   # PaperExchange
    exchange = get_exchange(paper_mode=False)  # CcxtExchange

Both implement the same interface:
    fetch_ticker(symbol) → dict
    fetch_ohlcv(symbol, timeframe, since, limit) → list
    create_order(symbol, type, side, amount, price) → dict
    cancel_order(order_id, symbol) → dict
    fetch_balance() → dict
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

import ccxt

from core.config import settings

logger = logging.getLogger(__name__)


class CcxtExchange:
    """Live exchange via ccxt."""

    def __init__(self, exchange_id: str | None = None) -> None:
        eid = exchange_id or settings.private_poller_exchange
        exchange_class = getattr(ccxt, eid, None)
        if exchange_class is None:
            raise ValueError(f"Unknown exchange: {eid}")

        config: dict = {"enableRateLimit": True}
        if settings.cryptocom_api_key:
            config["apiKey"] = settings.cryptocom_api_key
            config["secret"] = settings.cryptocom_api_secret

        self.exchange: ccxt.Exchange = exchange_class(config)
        self.exchange_id = eid

    def fetch_ticker(self, symbol: str) -> dict:
        return self.exchange.fetch_ticker(symbol)

    def fetch_ohlcv(
        self, symbol: str, timeframe: str = "1m", since: int | None = None, limit: int | None = None
    ) -> list:
        return self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)

    def create_order(
        self, symbol: str, order_type: str, side: str, amount: float, price: float | None = None
    ) -> dict:
        return self.exchange.create_order(symbol, order_type, side, amount, price)

    def cancel_order(self, order_id: str, symbol: str | None = None) -> dict:
        return self.exchange.cancel_order(order_id, symbol)

    def fetch_balance(self) -> dict:
        return self.exchange.fetch_balance()

    def fetch_orders(self, symbol: str | None = None, since: int | None = None, limit: int | None = None) -> list:
        return self.exchange.fetch_orders(symbol, since=since, limit=limit)


class PaperExchange:
    """Paper trading engine — market data passes through to real exchange,
    order calls are simulated locally using latest bid/ask from ohlcv_1m.
    """

    DEFAULT_MAKER_FEE = Decimal("0.0010")  # 0.10%
    DEFAULT_TAKER_FEE = Decimal("0.0025")  # 0.25%

    def __init__(self, exchange_id: str | None = None) -> None:
        self._live = CcxtExchange(exchange_id)
        self.exchange_id = self._live.exchange_id
        self._order_counter = 0

    # -- Market data: pass through to real exchange --

    def fetch_ticker(self, symbol: str) -> dict:
        return self._live.fetch_ticker(symbol)

    def fetch_ohlcv(
        self, symbol: str, timeframe: str = "1m", since: int | None = None, limit: int | None = None
    ) -> list:
        return self._live.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)

    def fetch_balance(self) -> dict:
        # Paper mode: balances come from paper_balances table, not exchange
        # Return empty — CLI reads from DB instead
        return {"total": {}, "free": {}, "used": {}}

    def fetch_orders(self, symbol: str | None = None, since: int | None = None, limit: int | None = None) -> list:
        # Paper orders are in our DB, not on exchange
        return []

    # -- Order operations: simulated locally --

    def create_order(
        self, symbol: str, order_type: str, side: str, amount: float, price: float | None = None
    ) -> dict:
        """Simulate order fill using latest ticker bid/ask."""
        ticker = self._live.fetch_ticker(symbol)

        if side == "buy":
            fill_price = float(ticker.get("ask") or ticker.get("last") or price or 0)
        else:
            fill_price = float(ticker.get("bid") or ticker.get("last") or price or 0)

        fee_rate = float(self.DEFAULT_TAKER_FEE if order_type == "market" else self.DEFAULT_MAKER_FEE)
        fee_cost = amount * fill_price * fee_rate

        self._order_counter += 1
        order_id = f"PAPER-{self._order_counter}"

        now = datetime.now(timezone.utc).isoformat()

        return {
            "id": order_id,
            "symbol": symbol,
            "type": order_type,
            "side": side,
            "amount": amount,
            "price": fill_price,
            "cost": amount * fill_price,
            "filled": amount,
            "remaining": 0,
            "status": "closed",
            "fee": {"cost": fee_cost, "currency": symbol.split("/")[1] if "/" in symbol else "USD"},
            "timestamp": now,
            "datetime": now,
            "paper": True,
        }

    def cancel_order(self, order_id: str, symbol: str | None = None) -> dict:
        """Paper orders are instantly filled, so cancel is a no-op."""
        return {"id": order_id, "status": "canceled"}


def get_exchange(paper_mode: bool | None = None) -> CcxtExchange | PaperExchange:
    """Factory — returns PaperExchange or CcxtExchange based on mode."""
    if paper_mode is None:
        paper_mode = settings.is_paper

    if paper_mode:
        return PaperExchange()
    return CcxtExchange()
