"""Data models for the trading toolkit."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


# ── Enums ────────────────────────────────────────────────────────────────────


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    LIMIT = "limit"
    MARKET = "market"


class OrderStatus(str, Enum):
    OPEN = "open"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class TransferType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    INTERNAL = "internal"


class VenueType(str, Enum):
    EXCHANGE = "exchange"
    DATA = "data"
    WALLET = "wallet"
    EXPLORER = "explorer"


class AccountType(str, Enum):
    SPOT = "spot"
    MARGIN = "margin"
    FUTURES = "futures"
    EARN = "earn"
    WALLET = "wallet"


# ── Data Models ──────────────────────────────────────────────────────────────


@dataclass
class OHLCV:
    asset_id: int
    venue_id: int
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    bid: Decimal | None = None
    ask: Decimal | None = None
    spread_pct: Decimal | None = None


@dataclass
class DailyOHLCV:
    asset_id: int
    venue_id: int
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    market_cap: Decimal | None = None


@dataclass
class Signal:
    strategy_name: str
    asset_symbol: str
    venue_code: str
    side: OrderSide
    confidence: float
    reasons: list[str] = field(default_factory=list)
    failed_conditions: list[str] = field(default_factory=list)
    indicators: dict[str, float] = field(default_factory=dict)
    suggested_price: Decimal | None = None
    suggested_stop_loss: Decimal | None = None
    suggested_take_profit: Decimal | None = None
    suggested_amount_usd: Decimal | None = None


@dataclass
class OrderRequest:
    asset_id: int
    venue_id: int
    account_id: int
    trading_pair_id: int
    strategy_id: int | None
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Decimal | None  # None for market orders
    stop_loss: Decimal | None
    take_profit: Decimal | None
    rationale: str | None = None
    paper: bool = True
