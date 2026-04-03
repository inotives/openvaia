"""Technical indicator computation using pandas-ta.

Two main functions:
- compute_daily(df)    → daily indicators from ohlcv_daily
- compute_intraday(df) → intraday indicators from ohlcv_1m
"""

from __future__ import annotations

import logging

import pandas as pd
import pandas_ta as ta

logger = logging.getLogger(__name__)


def compute_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Compute daily technical indicators from OHLCV data.

    Input columns: open, high, low, close, volume
    Output: DataFrame with all indicator columns matching indicators_daily schema.
    """
    if df.empty or len(df) < 2:
        return pd.DataFrame()

    result = pd.DataFrame(index=df.index)

    # Momentum
    result["rsi_14"] = ta.rsi(df["close"], length=14)
    result["rsi_7"] = ta.rsi(df["close"], length=7)
    stoch_rsi = ta.stochrsi(df["close"], length=14)
    if stoch_rsi is not None and not stoch_rsi.empty:
        result["stoch_rsi_k"] = stoch_rsi.iloc[:, 0]
        result["stoch_rsi_d"] = stoch_rsi.iloc[:, 1]

    # Trend (moving averages)
    result["ema_9"] = ta.ema(df["close"], length=9)
    result["ema_12"] = ta.ema(df["close"], length=12)
    result["ema_20"] = ta.ema(df["close"], length=20)
    result["ema_26"] = ta.ema(df["close"], length=26)
    result["ema_50"] = ta.ema(df["close"], length=50)
    result["ema_200"] = ta.ema(df["close"], length=200)
    result["sma_50"] = ta.sma(df["close"], length=50)
    result["sma_200"] = ta.sma(df["close"], length=200)

    # MACD
    macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
    if macd is not None and not macd.empty:
        result["macd"] = macd.iloc[:, 0]
        result["macd_signal"] = macd.iloc[:, 1]
        result["macd_hist"] = macd.iloc[:, 2]

    # Volatility
    result["atr_14"] = ta.atr(df["high"], df["low"], df["close"], length=14)
    bbands = ta.bbands(df["close"], length=20, std=2)
    if bbands is not None and not bbands.empty:
        result["bb_lower"] = bbands.iloc[:, 0]
        result["bb_upper"] = bbands.iloc[:, 2]
        mid = bbands.iloc[:, 1]
        result["bb_width"] = ((result["bb_upper"] - result["bb_lower"]) / mid * 100).where(mid != 0)

    # Trend strength
    adx_df = ta.adx(df["high"], df["low"], df["close"], length=14)
    if adx_df is not None and not adx_df.empty:
        result["adx_14"] = adx_df.iloc[:, 0]

    # Volume
    result["obv"] = ta.obv(df["close"], df["volume"])
    result["volume_sma_20"] = ta.sma(df["volume"], length=20)
    result["volume_ratio"] = (df["volume"] / result["volume_sma_20"]).where(result["volume_sma_20"] != 0)

    # Regime score: composite trend strength (0-100)
    # Based on: price vs EMAs, ADX, MACD histogram direction
    result["regime_score"] = _compute_regime_score(df, result)

    return result


def compute_intraday(df: pd.DataFrame) -> pd.DataFrame:
    """Compute intraday technical indicators from 1m candle data.

    Input columns: open, high, low, close, volume, bid, ask
    Output: DataFrame with indicator columns matching indicators_intraday schema.
    """
    if df.empty or len(df) < 2:
        return pd.DataFrame()

    result = pd.DataFrame(index=df.index)

    # Momentum
    result["rsi_14"] = ta.rsi(df["close"], length=14)
    result["rsi_7"] = ta.rsi(df["close"], length=7)
    stoch_rsi = ta.stochrsi(df["close"], length=14)
    if stoch_rsi is not None and not stoch_rsi.empty:
        result["stoch_rsi_k"] = stoch_rsi.iloc[:, 0]
        result["stoch_rsi_d"] = stoch_rsi.iloc[:, 1]

    # Trend
    result["ema_9"] = ta.ema(df["close"], length=9)
    result["ema_21"] = ta.ema(df["close"], length=21)
    result["ema_55"] = ta.ema(df["close"], length=55)

    # Volume & Price
    result["vwap"] = ta.vwap(df["high"], df["low"], df["close"], df["volume"])
    vol_sma = ta.sma(df["volume"], length=20)
    result["volume_ratio"] = (df["volume"] / vol_sma).where(vol_sma != 0)
    result["obv"] = ta.obv(df["close"], df["volume"])

    # Volatility
    if "bid" in df.columns and "ask" in df.columns:
        mid = (df["bid"] + df["ask"]) / 2
        result["spread_pct"] = ((df["ask"] - df["bid"]) / mid * 100).where(mid != 0)

    result["volatility_1h"] = df["close"].rolling(60).std()
    result["atr_14"] = ta.atr(df["high"], df["low"], df["close"], length=14)

    return result


def _compute_regime_score(ohlcv: pd.DataFrame, indicators: pd.DataFrame) -> pd.Series:
    """Compute a 0-100 regime score based on trend indicators.

    Components (each 0-20, summed to 0-100):
    1. Price vs EMA50: above = 20, below = 0
    2. Price vs EMA200: above = 20, below = 0
    3. EMA50 vs EMA200 (golden/death cross): above = 20, below = 0
    4. ADX strength: >25 = 20, 15-25 = 10, <15 = 0
    5. MACD histogram: positive = 20, negative = 0
    """
    score = pd.Series(0.0, index=ohlcv.index)

    close = ohlcv["close"]
    ema50 = indicators.get("ema_50")
    ema200 = indicators.get("ema_200")
    adx = indicators.get("adx_14")
    macd_hist = indicators.get("macd_hist")

    if ema50 is not None:
        score += (close > ema50).astype(float) * 20
    if ema200 is not None:
        score += (close > ema200).astype(float) * 20
    if ema50 is not None and ema200 is not None:
        score += (ema50 > ema200).astype(float) * 20
    if adx is not None:
        score += (adx > 25).astype(float) * 20
        # Partial credit for moderate ADX
        score += ((adx >= 15) & (adx <= 25)).astype(float) * 10
        score -= ((adx >= 15) & (adx <= 25)).astype(float) * 10  # remove double count
        # Simplified: strong = 20, moderate = 10, weak = 0
        adx_score = pd.Series(0.0, index=ohlcv.index)
        adx_score = adx_score.where(adx < 15, 10.0)
        adx_score = adx_score.where(adx < 25, 20.0)
        score = score - ((adx > 25).astype(float) * 20) + adx_score  # replace simple logic
    if macd_hist is not None:
        score += (macd_hist > 0).astype(float) * 20

    return score.clip(0, 100)
