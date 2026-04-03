"""Tests for exchange wrapper — paper mode simulation."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.exchange import CcxtExchange, PaperExchange, get_exchange


class TestPaperExchange:
    def setup_method(self):
        """Create PaperExchange with mocked live exchange."""
        self.paper = PaperExchange.__new__(PaperExchange)
        self.paper._live = MagicMock()
        self.paper._live.exchange_id = "cryptocom"
        self.paper.exchange_id = "cryptocom"
        self.paper._order_counter = 0

    def test_fetch_ticker_passes_through(self):
        self.paper._live.fetch_ticker.return_value = {"bid": 0.084, "ask": 0.085, "last": 0.0845}
        result = self.paper.fetch_ticker("CRO/USDT")
        self.paper._live.fetch_ticker.assert_called_once_with("CRO/USDT")
        assert result["bid"] == 0.084

    def test_fetch_ohlcv_passes_through(self):
        self.paper._live.fetch_ohlcv.return_value = [[1, 0.08, 0.09, 0.07, 0.085, 1000]]
        result = self.paper.fetch_ohlcv("CRO/USDT", "1m")
        assert len(result) == 1

    def test_create_order_buy_fills_at_ask(self):
        self.paper._live.fetch_ticker.return_value = {"bid": 0.084, "ask": 0.085, "last": 0.0845}
        order = self.paper.create_order("CRO/USDT", "market", "buy", 1000)
        assert order["price"] == 0.085  # ask price
        assert order["filled"] == 1000
        assert order["status"] == "closed"
        assert order["paper"] is True
        assert order["id"].startswith("PAPER-")

    def test_create_order_sell_fills_at_bid(self):
        self.paper._live.fetch_ticker.return_value = {"bid": 0.084, "ask": 0.085, "last": 0.0845}
        order = self.paper.create_order("CRO/USDT", "market", "sell", 1000)
        assert order["price"] == 0.084  # bid price

    def test_create_order_limit_uses_maker_fee(self):
        self.paper._live.fetch_ticker.return_value = {"bid": 0.084, "ask": 0.085, "last": 0.0845}
        order = self.paper.create_order("CRO/USDT", "limit", "buy", 1000, price=0.083)
        # Maker fee = 0.10%
        expected_fee = 1000 * 0.085 * 0.001  # amount * fill_price * maker_fee
        assert abs(order["fee"]["cost"] - expected_fee) < 0.01

    def test_create_order_market_uses_taker_fee(self):
        self.paper._live.fetch_ticker.return_value = {"bid": 0.084, "ask": 0.085, "last": 0.0845}
        order = self.paper.create_order("CRO/USDT", "market", "buy", 1000)
        # Taker fee = 0.25%
        expected_fee = 1000 * 0.085 * 0.0025
        assert abs(order["fee"]["cost"] - expected_fee) < 0.01

    def test_order_ids_increment(self):
        self.paper._live.fetch_ticker.return_value = {"bid": 0.084, "ask": 0.085, "last": 0.0845}
        o1 = self.paper.create_order("CRO/USDT", "market", "buy", 100)
        o2 = self.paper.create_order("CRO/USDT", "market", "sell", 100)
        assert o1["id"] != o2["id"]

    def test_cancel_order_noop(self):
        result = self.paper.cancel_order("PAPER-1")
        assert result["status"] == "canceled"

    def test_fetch_balance_returns_empty(self):
        result = self.paper.fetch_balance()
        assert result == {"total": {}, "free": {}, "used": {}}

    def test_fetch_orders_returns_empty(self):
        result = self.paper.fetch_orders()
        assert result == []


class TestGetExchange:
    @patch.object(PaperExchange, "__init__", return_value=None)
    def test_paper_mode_returns_paper(self, _):
        ex = get_exchange(paper_mode=True)
        assert isinstance(ex, PaperExchange)

    @patch.object(CcxtExchange, "__init__", return_value=None)
    def test_live_mode_returns_ccxt(self, _):
        ex = get_exchange(paper_mode=False)
        assert isinstance(ex, CcxtExchange)
