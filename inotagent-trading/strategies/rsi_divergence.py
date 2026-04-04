"""RSI Divergence strategy — "The Contrarian"

Catches reversals by detecting bullish divergence: price makes a lower low
but RSI makes a higher low, signaling selling exhaustion.

Entry conditions:
1. Regime 15-50 (not crashing, not strong trend)
2. Price made a lower low vs N days ago
3. RSI made a higher low vs N days ago (bullish divergence)
4. RSI < 45 (still in oversold territory, not already recovered)
5. ATR% stable (not a crash in progress)

Exit:
- Take profit when RSI crosses above 55 (momentum recovered)
- Or price reaches EMA(20)
- Stop loss: -4% hard stop
- Time stop: 5 days if not in profit
"""

from __future__ import annotations

from strategies.base import BaseStrategy, Signal


class RSIDivergenceStrategy(BaseStrategy):
    name = "rsi_divergence"
    strategy_type = "rsi_divergence"

    def evaluate_signal(self, daily: dict, intraday: dict | None = None) -> Signal:
        reasons = []
        failed = []
        indicators = {}

        close = daily.get("close")
        if close is None:
            return Signal(side="none", confidence=0.0, failed_conditions=["No close price"])
        indicators["close"] = float(close)

        conditions_total = 5
        conditions_met = 0

        # 1. Regime filter: 15-50 (not crash, not strong trend)
        regime = daily.get("regime_score")
        regime_min = self.entry.get("regime_min", 15)
        regime_max = self.entry.get("regime_max", 50)
        if regime is not None:
            indicators["regime_score"] = float(regime)
            if regime_min <= regime <= regime_max:
                reasons.append(f"Regime {regime:.0f} in [{regime_min}-{regime_max}]")
                conditions_met += 1
            else:
                failed.append(f"Regime {regime:.0f} outside [{regime_min}-{regime_max}]")

        # 2 & 3. Divergence: price lower low + RSI higher low
        close_prev = daily.get("close_prev_n")  # N days ago close
        rsi = daily.get("rsi_14")
        rsi_prev = daily.get("rsi_14_prev_n")  # N days ago RSI

        if close_prev is not None and rsi is not None and rsi_prev is not None:
            price_lower = float(close) < float(close_prev)
            rsi_higher = float(rsi) > float(rsi_prev)

            indicators["close_prev_n"] = float(close_prev)
            indicators["rsi_14"] = float(rsi)
            indicators["rsi_14_prev_n"] = float(rsi_prev)

            if price_lower:
                reasons.append(f"Price lower low: {close:.6f} < {close_prev:.6f}")
                conditions_met += 1
            else:
                failed.append(f"No price lower low: {close:.6f} >= {close_prev:.6f}")

            if rsi_higher:
                reasons.append(f"RSI higher low: {rsi:.1f} > {rsi_prev:.1f} (bullish divergence)")
                conditions_met += 1
            else:
                failed.append(f"No RSI divergence: {rsi:.1f} <= {rsi_prev:.1f}")
        else:
            # If historical data not available, check what we have
            if rsi is not None:
                indicators["rsi_14"] = float(rsi)
            conditions_total -= 2  # Can't evaluate divergence

        # 4. RSI still oversold (not already recovered)
        rsi_max = self.entry.get("rsi_max", 45)
        if rsi is not None:
            if rsi < rsi_max:
                reasons.append(f"RSI {rsi:.1f} < {rsi_max} (still oversold)")
                conditions_met += 1
            else:
                failed.append(f"RSI {rsi:.1f} >= {rsi_max} (already recovering)")

        # 5. ATR% stable
        atr = daily.get("atr_14")
        max_atr_pct = self.entry.get("max_atr_pct", 5.0)
        if atr is not None and float(close) > 0:
            atr_pct = float(atr) / float(close) * 100
            indicators["atr_pct"] = round(atr_pct, 2)
            if atr_pct < max_atr_pct:
                reasons.append(f"ATR% = {atr_pct:.1f}% < {max_atr_pct}% (stable)")
                conditions_met += 1
            else:
                failed.append(f"ATR% = {atr_pct:.1f}% >= {max_atr_pct}% (crash risk)")

        # Need divergence (conditions 2+3) plus at least 2 others
        has_divergence = any("divergence" in r.lower() for r in reasons)
        min_conditions = self.entry.get("min_conditions", 4)
        confidence = conditions_met / conditions_total if conditions_total > 0 else 0.0

        side = "buy" if conditions_met >= min_conditions and has_divergence else "none"

        return Signal(
            side=side,
            confidence=round(confidence, 4),
            reasons=reasons,
            failed_conditions=failed,
            indicators=indicators,
        )

    def should_exit(self, entry_price: float, current_price: float, daily: dict) -> Signal | None:
        if entry_price <= 0:
            return None

        pnl_pct = (current_price - entry_price) / entry_price * 100

        # Hard stop
        stop_pct = self.exit.get("stop_loss_pct", 4.0)
        if pnl_pct <= -stop_pct:
            return Signal(
                side="sell", confidence=1.0,
                reasons=[f"Stop loss: {pnl_pct:.1f}% <= -{stop_pct}%"],
            )

        # RSI recovered above threshold
        rsi = daily.get("rsi_14")
        rsi_exit = self.exit.get("rsi_exit_threshold", 55)
        if rsi is not None and rsi > rsi_exit:
            return Signal(
                side="sell", confidence=0.9,
                reasons=[f"RSI recovered: {rsi:.1f} > {rsi_exit} (PnL {pnl_pct:+.1f}%)"],
            )

        # Price reaches EMA(20)
        ema_20 = daily.get("ema_20")
        if ema_20 is not None and current_price >= float(ema_20) and pnl_pct > 0:
            return Signal(
                side="sell", confidence=0.85,
                reasons=[f"EMA(20) reached: {current_price:.6f} >= {ema_20:.6f} (PnL {pnl_pct:+.1f}%)"],
            )

        # Time stop
        max_hold_days = self.exit.get("max_hold_days", 5)
        days_held = daily.get("days_held", 0)
        if days_held >= max_hold_days and pnl_pct <= 0:
            return Signal(
                side="sell", confidence=0.8,
                reasons=[f"Time stop: {days_held} days, no profit ({pnl_pct:+.1f}%)"],
            )

        return None
