"""Sentiment score computation for grid parameter adjustment.

Combines:
1. Fear & Greed Index (from indicators_daily.custom)
2. Funding rate (from indicators_intraday.custom)
3. Robin's news score (from research reports — optional)

Output: -1.0 (extreme fear) to +1.0 (extreme greed)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def normalize_fear_greed(fgi: int | None) -> float:
    """Normalize Fear & Greed Index (0-100) to -1.0 to +1.0."""
    if fgi is None:
        return 0.0
    if fgi <= 25:
        return -1.0
    if fgi <= 45:
        return -0.5
    if fgi <= 55:
        return 0.0
    if fgi <= 75:
        return 0.5
    return 1.0


def normalize_funding_rate(rate: float | None) -> float:
    """Normalize funding rate to -0.5 to +1.0 signal."""
    if rate is None:
        return 0.0
    if rate < -0.0001:  # -0.01%
        return -0.5  # bearish leverage, contrarian buy
    if rate > 0.0003:  # +0.03%
        return 1.0   # extreme bullish, high dump risk
    if rate > 0.0001:  # +0.01%
        return 0.5   # bullish leverage, caution
    return 0.0


def compute_sentiment_score(
    fear_greed_index: int | None = None,
    funding_rate: float | None = None,
    news_score: float | None = None,
    weights: dict | None = None,
) -> tuple[float, str]:
    """Compute composite sentiment score.

    Returns (score, classification).
    Score range: -1.0 (extreme fear) to +1.0 (extreme greed).
    """
    w = weights or {"fear_greed": 0.5, "funding_rate": 0.3, "news": 0.2}

    fg_signal = normalize_fear_greed(fear_greed_index)
    fr_signal = normalize_funding_rate(funding_rate)
    news_signal = news_score if news_score is not None else 0.0

    score = (
        fg_signal * w.get("fear_greed", 0.5) +
        fr_signal * w.get("funding_rate", 0.3) +
        news_signal * w.get("news", 0.2)
    )

    # Classify
    if score <= -0.7:
        classification = "extreme_fear"
    elif score <= -0.3:
        classification = "fear"
    elif score <= 0.3:
        classification = "neutral"
    elif score <= 0.7:
        classification = "greed"
    else:
        classification = "extreme_greed"

    return round(score, 4), classification


def get_sentiment_adjustments(classification: str, config: dict | None = None) -> dict:
    """Get grid parameter adjustments for a sentiment classification.

    Returns dict with: capital_multiplier, profit_target_pct (optional), atr_multiplier_override (optional).
    """
    defaults = {
        "extreme_fear":  {"capital_multiplier": 1.5, "profit_target_pct": 2.5, "atr_multiplier_override": 0.7},
        "fear":          {"capital_multiplier": 1.0},
        "neutral":       {"capital_multiplier": 1.0},
        "greed":         {"capital_multiplier": 0.5, "profit_target_pct": 1.0},
        "extreme_greed": {"capital_multiplier": 0.0},
    }

    if config and "adjustments" in config:
        return config["adjustments"].get(classification, defaults.get(classification, {}))

    return defaults.get(classification, {"capital_multiplier": 1.0})


def load_sentiment_data(conn, schema: str, asset_symbol: str) -> dict:
    """Load sentiment data from DB for an asset.

    Returns dict with fear_greed_index, funding_rate, and whatever's available.
    """
    s = schema
    data = {"fear_greed_index": None, "funding_rate": None}

    # Fear & Greed from daily indicators custom JSONB
    cur = conn.execute(
        f"""SELECT custom FROM {s}.indicators_daily
            WHERE asset_id = (SELECT id FROM {s}.assets WHERE symbol = %s)
            ORDER BY date DESC LIMIT 1""",
        (asset_symbol.upper(),),
    )
    row = cur.fetchone()
    if row and row["custom"] and isinstance(row["custom"], dict):
        data["fear_greed_index"] = row["custom"].get("fear_greed_index")
        data["fear_greed_class"] = row["custom"].get("fear_greed_class")

    # Funding rate from intraday indicators custom JSONB
    cur = conn.execute(
        f"""SELECT custom FROM {s}.indicators_intraday
            WHERE asset_id = (SELECT id FROM {s}.assets WHERE symbol = %s)
            ORDER BY timestamp DESC LIMIT 1""",
        (asset_symbol.upper(),),
    )
    row = cur.fetchone()
    if row and row["custom"] and isinstance(row["custom"], dict):
        data["funding_rate"] = row["custom"].get("funding_rate")

    return data
