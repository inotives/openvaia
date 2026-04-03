"""Momentum strategy — RSI oversold + EMA crossover + ADX trend strength.

Entry conditions (all weighted):
- RSI(14) below threshold (oversold)
- EMA fast > EMA slow (bullish crossover)
- ADX > minimum (strong trend)
- Volume ratio above threshold
- Regime score above threshold

Exit conditions:
- Take profit %
- Stop loss %
- Trailing stop (ATR-based)
"""

from __future__ import annotations

from strategies.base import BaseStrategy, Signal


class MomentumStrategy(BaseStrategy):
    name = "momentum"
    strategy_type = "momentum"

    def evaluate_signal(self, daily: dict, intraday: dict | None = None) -> Signal:
        reasons = []
        failed = []
        indicators = {}
        weights_met = 0.0
        weights_total = 0.0

        condition_weights = self.entry.get("condition_weights", {})

        # RSI
        rsi = daily.get("rsi_14")
        threshold = self.entry.get("rsi_buy_threshold", 30)
        w = condition_weights.get("rsi", 2)
        weights_total += w
        if rsi is not None:
            indicators["rsi_14"] = float(rsi)
            if rsi < threshold:
                reasons.append(f"RSI(14) = {rsi:.1f} < {threshold} (oversold)")
                weights_met += w
            else:
                failed.append(f"RSI(14) = {rsi:.1f} >= {threshold}")

        # EMA crossover (from intraday if available, else daily)
        src = intraday or daily
        ema_fast_key = "ema_9"
        ema_slow_key = "ema_21"
        ema_fast = src.get(ema_fast_key)
        ema_slow = src.get(ema_slow_key)
        w = condition_weights.get("ema_cross", 2)
        weights_total += w
        if ema_fast is not None and ema_slow is not None:
            indicators[ema_fast_key] = float(ema_fast)
            indicators[ema_slow_key] = float(ema_slow)
            if ema_fast > ema_slow:
                reasons.append(f"EMA(9) > EMA(21) (bullish)")
                weights_met += w
            else:
                failed.append(f"EMA(9) <= EMA(21)")

        # ADX
        adx = daily.get("adx_14")
        min_adx = self.entry.get("min_adx", 25)
        w = condition_weights.get("adx", 1)
        weights_total += w
        if adx is not None:
            indicators["adx_14"] = float(adx)
            if adx > min_adx:
                reasons.append(f"ADX(14) = {adx:.1f} > {min_adx} (strong trend)")
                weights_met += w
            else:
                failed.append(f"ADX(14) = {adx:.1f} <= {min_adx}")

        # Volume ratio
        vol_ratio = (intraday or daily).get("volume_ratio")
        min_vol = self.entry.get("volume_ratio_min", 1.5)
        w = condition_weights.get("volume", 1)
        weights_total += w
        if vol_ratio is not None:
            indicators["volume_ratio"] = float(vol_ratio)
            if vol_ratio > min_vol:
                reasons.append(f"Volume ratio = {vol_ratio:.1f} > {min_vol}")
                weights_met += w
            else:
                failed.append(f"Volume ratio = {vol_ratio:.1f} <= {min_vol}")

        # Regime score
        regime = daily.get("regime_score")
        min_regime = self.entry.get("min_regime_score", 61)
        w = condition_weights.get("regime", 3)
        weights_total += w
        if regime is not None:
            indicators["regime_score"] = float(regime)
            if regime > min_regime:
                reasons.append(f"Regime = {regime:.0f} > {min_regime}")
                weights_met += w
            else:
                failed.append(f"Regime = {regime:.0f} <= {min_regime}")

        confidence = weights_met / weights_total if weights_total > 0 else 0.0

        side = "buy" if confidence >= 0.50 and len(reasons) > 0 else "none"

        return Signal(
            side=side,
            confidence=round(confidence, 4),
            reasons=reasons,
            failed_conditions=failed,
            indicators=indicators,
        )


# Registry of strategy types — import here to keep get_strategy() as single entry point
from strategies.bollinger import BollingerStrategy
from strategies.trend_follow import TrendFollowStrategy
from strategies.volatility_breakout import VolatilityBreakoutStrategy
from strategies.mean_reversion import MeanReversionStrategy
from strategies.rsi_divergence import RSIDivergenceStrategy

STRATEGY_REGISTRY: dict[str, type[BaseStrategy]] = {
    "momentum": MomentumStrategy,
    "bollinger": BollingerStrategy,
    "trend_follow": TrendFollowStrategy,
    "volatility_breakout": VolatilityBreakoutStrategy,
    "mean_reversion": MeanReversionStrategy,
    "rsi_divergence": RSIDivergenceStrategy,
}


def get_strategy(strategy_type: str, params: dict) -> BaseStrategy:
    """Factory — returns strategy instance by type."""
    cls = STRATEGY_REGISTRY.get(strategy_type)
    if not cls:
        raise ValueError(f"Unknown strategy type: {strategy_type}. Available: {list(STRATEGY_REGISTRY.keys())}")
    return cls(params)
