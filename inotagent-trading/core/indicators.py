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
    result["ema_8"] = ta.ema(df["close"], length=8)
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

    # Keltner Channels (for squeeze detection)
    kc = ta.kc(df["high"], df["low"], df["close"], length=20, scalar=1.5)
    if kc is not None and not kc.empty:
        result["kc_lower"] = kc.iloc[:, 0]
        result["kc_upper"] = kc.iloc[:, 2]
        # Squeeze: BB inside Keltner
        if "bb_upper" in result and "bb_lower" in result:
            result["squeeze"] = (
                (result["bb_upper"] < result["kc_upper"]) &
                (result["bb_lower"] > result["kc_lower"])
            ).astype(float)

    # 20-day high (for breakout detection)
    result["high_20d"] = df["high"].rolling(20).max()

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
    """Compute a 0-100 regime score from three normalized components.

    RS = (score_adx × 0.4) + (score_slope × 0.4) + (score_vol × 0.2)

    Component 1: ADX(14) — trend strength (weight 0.4)
        ADX <= 15 → 0, ADX = 25 → 50, ADX >= 40 → 100

    Component 2: EMA50 slope 5d% — trend direction & velocity (weight 0.4)
        slope <= 0% → 0, slope >= 0.5% → 100

    Component 3: Volatility ratio ATR(14)/StdDev(14) — noise filter (weight 0.2, inverted)
        ratio >= 1.2 → 0, ratio <= 0.8 → 100
    """
    score = pd.Series(0.0, index=ohlcv.index)

    # Component 1: ADX normalized (piecewise linear)
    adx = indicators.get("adx_14")
    if adx is not None:
        score_adx = pd.Series(0.0, index=ohlcv.index)
        mask_mid = (adx > 15) & (adx < 25)
        mask_high = (adx >= 25) & (adx < 40)
        mask_max = adx >= 40

        score_adx = score_adx.where(~mask_mid, (adx - 15) / 10 * 50)
        score_adx = score_adx.where(~mask_high, 50 + (adx - 25) / 15 * 50)
        score_adx = score_adx.where(~mask_max, 100.0)
    else:
        score_adx = pd.Series(0.0, index=ohlcv.index)

    # Component 2: EMA50 slope over 5 days (%)
    ema50 = indicators.get("ema_50")
    if ema50 is not None:
        ema50_5d_ago = ema50.shift(5)
        slope_pct = ((ema50 - ema50_5d_ago) / ema50_5d_ago * 100).fillna(0)
        score_slope = (slope_pct / 0.5 * 100).clip(0, 100)
    else:
        score_slope = pd.Series(0.0, index=ohlcv.index)

    # Component 3: Volatility ratio (inverted — low noise = high score)
    atr = indicators.get("atr_14")
    if atr is not None:
        std_dev = ohlcv["close"].rolling(14).std()
        vol_ratio = (atr / std_dev).where(std_dev > 0, 1.0)
        score_vol = ((1.2 - vol_ratio) / 0.4 * 100).clip(0, 100)
    else:
        score_vol = pd.Series(0.0, index=ohlcv.index)

    # Weighted composite
    score = score_adx * 0.4 + score_slope * 0.4 + score_vol * 0.2

    return score.clip(0, 100)
