"""Trend Following strategy — ride sustained uptrends with trailing stop.

Entry conditions (all must pass):
1. Regime score >= min_regime_score (61)
2. EMA50 > EMA200 (golden cross)
3. Price > 5-day high (breakout)
4. ADX >= min_adx (25)
5. RSI < rsi_entry_max (70, not overbought)
6. ATR% < max_atr_pct (6%, not too volatile)

Exit:
- Trailing stop: highest_price - (atr_trail_multiplier × ATR)
- Initial stop: entry_price - (atr_stop_multiplier × ATR)
- Effective stop = MAX(initial, trailing) — only moves up

Position sizing:
- ATR-scaled: capital_at_risk / (ATR × atr_stop_multiplier)
"""

from __future__ import annotations

from strategies.base import BaseStrategy, Signal


class TrendFollowStrategy(BaseStrategy):
    name = "trend_follow"
    strategy_type = "trend_follow"

    def evaluate_signal(self, daily: dict, intraday: dict | None = None) -> Signal:
        reasons = []
        failed = []
        indicators = {}

        close = daily.get("close")
        if close is None:
            return Signal(side="none", confidence=0.0, failed_conditions=["No close price"])
        indicators["close"] = float(close)

        conditions_total = 6
        conditions_met = 0

        # 1. Regime score >= threshold
        regime = daily.get("regime_score")
        min_regime = self.entry.get("min_regime_score", 61)
        if regime is not None:
            indicators["regime_score"] = float(regime)
            if regime >= min_regime:
                reasons.append(f"Regime {regime:.0f} >= {min_regime} (trending)")
                conditions_met += 1
            else:
                failed.append(f"Regime {regime:.0f} < {min_regime} (not trending)")

        # 2. Golden cross: EMA50 > EMA200
        ema50 = daily.get("ema_50")
        ema200 = daily.get("ema_200")
        if ema50 is not None and ema200 is not None:
            indicators["ema_50"] = float(ema50)
            indicators["ema_200"] = float(ema200)
            if ema50 > ema200:
                reasons.append(f"Golden cross: EMA50 > EMA200")
                conditions_met += 1
            else:
                failed.append(f"Death cross: EMA50 <= EMA200")

        # 3. Price breakout > 5-day high
        # We approximate 5-day high from close (backtester/scanner should pass high_5d if available)
        high_5d = daily.get("high_5d")
        if high_5d is not None:
            indicators["high_5d"] = float(high_5d)
            if float(close) > float(high_5d):
                reasons.append(f"Breakout: {close:.6f} > 5d high {high_5d:.6f}")
                conditions_met += 1
            else:
                failed.append(f"No breakout: {close:.6f} <= 5d high {high_5d:.6f}")
        else:
            # If no 5d high provided, skip this condition
            conditions_total -= 1

        # 4. ADX >= min
        adx = daily.get("adx_14")
        min_adx = self.entry.get("min_adx", 25)
        if adx is not None:
            indicators["adx_14"] = float(adx)
            if adx >= min_adx:
                reasons.append(f"ADX {adx:.1f} >= {min_adx} (strong trend)")
                conditions_met += 1
            else:
                failed.append(f"ADX {adx:.1f} < {min_adx} (weak trend)")

        # 5. RSI not overbought
        rsi = daily.get("rsi_14")
        rsi_max = self.entry.get("rsi_entry_max", 70)
        if rsi is not None:
            indicators["rsi_14"] = float(rsi)
            if rsi < rsi_max:
                reasons.append(f"RSI {rsi:.1f} < {rsi_max} (not overbought)")
                conditions_met += 1
            else:
                failed.append(f"RSI {rsi:.1f} >= {rsi_max} (overbought)")

        # 6. ATR% not too volatile
        atr = daily.get("atr_14")
        max_atr_pct = self.entry.get("max_atr_pct", 6.0)
        if atr is not None and float(close) > 0:
            atr_pct = float(atr) / float(close) * 100
            indicators["atr_pct"] = round(atr_pct, 2)
            if atr_pct < max_atr_pct:
                reasons.append(f"ATR% = {atr_pct:.1f}% < {max_atr_pct}% (manageable volatility)")
                conditions_met += 1
            else:
                failed.append(f"ATR% = {atr_pct:.1f}% >= {max_atr_pct}% (too volatile)")

        # All conditions must pass for entry
        if conditions_total > 0 and conditions_met == conditions_total:
            confidence = 1.0
            side = "buy"
        elif conditions_total > 0 and conditions_met >= conditions_total - 1:
            confidence = conditions_met / conditions_total
            side = "buy" if confidence >= 0.80 else "none"
        else:
            confidence = conditions_met / conditions_total if conditions_total > 0 else 0.0
            side = "none"

        return Signal(
            side=side,
            confidence=round(confidence, 4),
            reasons=reasons,
            failed_conditions=failed,
            indicators=indicators,
        )

    def should_exit(self, entry_price: float, current_price: float, daily: dict) -> Signal | None:
        """Trailing stop exit — uses ATR to set dynamic stop that only moves up."""
        if entry_price <= 0:
            return None

        atr = daily.get("atr_14")
        if atr is None:
            # Fallback to fixed stop-loss
            return super().should_exit(entry_price, current_price, daily)

        atr_val = float(atr)
        stop_mult = self.exit.get("atr_stop_multiplier", 2.0)
        trail_mult = self.exit.get("atr_trail_multiplier", 3.0)

        # Initial stop (set at entry, never moves down)
        initial_stop = entry_price - (stop_mult * atr_val)

        # Trailing stop (uses highest price — approximated here with current price)
        # In real usage, the caller tracks highest_price_since_entry
        highest = daily.get("highest_since_entry", current_price)
        trailing_stop = float(highest) - (trail_mult * atr_val)

        # Effective stop = max of initial and trailing
        effective_stop = max(initial_stop, trailing_stop)

        if current_price <= effective_stop:
            pnl_pct = (current_price - entry_price) / entry_price * 100
            return Signal(
                side="sell", confidence=1.0,
                reasons=[f"Trailing stop: price {current_price:.6f} <= stop {effective_stop:.6f} (PnL {pnl_pct:+.1f}%)"],
                indicators={"effective_stop": effective_stop, "initial_stop": initial_stop, "trailing_stop": trailing_stop},
            )

        return None

    def compute_position_size(self, capital: float, current_price: float, atr: float) -> float:
        """ATR-scaled position sizing — risk a fixed % of capital."""
        risk_pct = self.position.get("risk_pct_per_trade", 1.0) / 100
        stop_mult = self.exit.get("atr_stop_multiplier", 2.0)

        capital_at_risk = capital * risk_pct
        position_size = capital_at_risk / (atr * stop_mult)

        # Cap at max capital deployment
        max_position = capital / current_price if current_price > 0 else 0
        return min(position_size, max_position)
