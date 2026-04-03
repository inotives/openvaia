"""Tests for technical indicator computation."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.indicators import compute_daily, compute_intraday


def _make_ohlcv(n: int = 250, base_price: float = 100.0) -> pd.DataFrame:
    """Generate synthetic OHLCV data with a trend for testing."""
    np.random.seed(42)
    dates = pd.date_range("2025-01-01", periods=n, freq="D")

    # Random walk with slight upward drift
    returns = np.random.normal(0.001, 0.02, n)
    prices = base_price * np.cumprod(1 + returns)

    return pd.DataFrame({
        "open": prices * (1 + np.random.uniform(-0.005, 0.005, n)),
        "high": prices * (1 + np.random.uniform(0, 0.02, n)),
        "low": prices * (1 - np.random.uniform(0, 0.02, n)),
        "close": prices,
        "volume": np.random.uniform(1e6, 5e6, n),
    }, index=dates)


def _make_intraday(n: int = 120) -> pd.DataFrame:
    """Generate synthetic 1m candle data with bid/ask."""
    np.random.seed(42)
    timestamps = pd.date_range("2025-06-01 09:00", periods=n, freq="1min")

    returns = np.random.normal(0, 0.001, n)
    prices = 100.0 * np.cumprod(1 + returns)

    df = pd.DataFrame({
        "open": prices * (1 + np.random.uniform(-0.001, 0.001, n)),
        "high": prices * (1 + np.random.uniform(0, 0.005, n)),
        "low": prices * (1 - np.random.uniform(0, 0.005, n)),
        "close": prices,
        "volume": np.random.uniform(1e3, 5e3, n),
    }, index=timestamps)

    df["bid"] = prices * 0.9999
    df["ask"] = prices * 1.0001

    return df


class TestComputeDaily:
    def setup_method(self):
        self.df = _make_ohlcv(250)
        self.result = compute_daily(self.df)

    def test_returns_dataframe(self):
        assert isinstance(self.result, pd.DataFrame)
        assert len(self.result) == 250

    def test_rsi_columns(self):
        assert "rsi_14" in self.result.columns
        assert "rsi_7" in self.result.columns
        # RSI should be between 0 and 100 (where not NaN)
        valid = self.result["rsi_14"].dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_ema_columns(self):
        for col in ["ema_9", "ema_12", "ema_20", "ema_26", "ema_50", "ema_200"]:
            assert col in self.result.columns

    def test_sma_columns(self):
        assert "sma_50" in self.result.columns
        assert "sma_200" in self.result.columns

    def test_macd_columns(self):
        assert "macd" in self.result.columns
        assert "macd_signal" in self.result.columns
        assert "macd_hist" in self.result.columns

    def test_volatility_columns(self):
        assert "atr_14" in self.result.columns
        assert "bb_upper" in self.result.columns
        assert "bb_lower" in self.result.columns
        assert "bb_width" in self.result.columns
        # BB upper should be above BB lower
        valid_idx = self.result["bb_upper"].dropna().index
        assert (self.result.loc[valid_idx, "bb_upper"] >= self.result.loc[valid_idx, "bb_lower"]).all()

    def test_adx_column(self):
        assert "adx_14" in self.result.columns

    def test_volume_columns(self):
        assert "obv" in self.result.columns
        assert "volume_sma_20" in self.result.columns
        assert "volume_ratio" in self.result.columns

    def test_regime_score(self):
        assert "regime_score" in self.result.columns
        valid = self.result["regime_score"].dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_stoch_rsi(self):
        assert "stoch_rsi_k" in self.result.columns
        assert "stoch_rsi_d" in self.result.columns

    def test_empty_input(self):
        result = compute_daily(pd.DataFrame())
        assert result.empty

    def test_too_few_rows(self):
        result = compute_daily(self.df.head(1))
        assert result.empty


class TestComputeIntraday:
    def setup_method(self):
        self.df = _make_intraday(120)
        self.result = compute_intraday(self.df)

    def test_returns_dataframe(self):
        assert isinstance(self.result, pd.DataFrame)
        assert len(self.result) == 120

    def test_momentum_columns(self):
        assert "rsi_14" in self.result.columns
        assert "rsi_7" in self.result.columns

    def test_trend_columns(self):
        assert "ema_9" in self.result.columns
        assert "ema_21" in self.result.columns
        assert "ema_55" in self.result.columns

    def test_vwap(self):
        assert "vwap" in self.result.columns

    def test_volume_columns(self):
        assert "volume_ratio" in self.result.columns
        assert "obv" in self.result.columns

    def test_spread_pct(self):
        assert "spread_pct" in self.result.columns
        valid = self.result["spread_pct"].dropna()
        # Spread should be positive (ask > bid)
        assert (valid >= 0).all()

    def test_volatility_columns(self):
        assert "volatility_1h" in self.result.columns
        assert "atr_14" in self.result.columns

    def test_empty_input(self):
        result = compute_intraday(pd.DataFrame())
        assert result.empty

    def test_no_bid_ask_columns(self):
        df = self.df.drop(columns=["bid", "ask"])
        result = compute_intraday(df)
        assert "spread_pct" not in result.columns or result["spread_pct"].isna().all()
