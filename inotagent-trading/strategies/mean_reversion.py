"""Mean Reversion strategy — "The Range Specialist"

Active in low-trend sideways markets (regime 20-40). Bets that price
stretching below the mean will snap back.

Entry conditions:
1. Regime between 20-40 (sideways, not trending or crashing)
2. Close below lower BB(20,2) — the "stretch"
3. RSI < 30 AND RSI turning up (momentum exhaustion + divergence)
4. ATR% low/stable — drifting move, not crashing

Exit:
- Primary: price touches SMA(20) — the "mean"
- Secondary: if volume spikes, hold to upper BB
- Stop loss: -3% hard stop or close below recent swing low
- Time stop: 48h / 2 days — if snap-back doesn't happen, trade is broken

Size: 12% of capital (higher conviction in ranging markets)
"""

from __future__ import annotations

from strategies.base import BaseStrategy, Signal


class MeanReversionStrategy(BaseStrategy):
    name = "mean_reversion"
    strategy_type = "mean_reversion"

    def evaluate_signal(self, daily: dict, intraday: dict | None = None) -> Signal:
        reasons = []
        failed = []
        indicators = {}

        close = daily.get("close")
        if close is None:
            return Signal(side="none", confidence=0.0, failed_conditions=["No close price"])
        indicators["close"] = float(close)

        conditions_total = 4
        conditions_met = 0

        # 1. Regime filter: must be in sideways range (20-40)
        regime = daily.get("regime_score")
        regime_min = self.entry.get("regime_min", 20)
        regime_max = self.entry.get("regime_max", 40)
        if regime is not None:
            indicators["regime_score"] = float(regime)
            if regime_min <= regime <= regime_max:
                reasons.append(f"Regime {regime:.0f} in range [{regime_min}-{regime_max}] (sideways)")
                conditions_met += 1
            else:
                failed.append(f"Regime {regime:.0f} outside [{regime_min}-{regime_max}]")

        # 2. Price below lower BB — the "stretch"
        bb_lower = daily.get("bb_lower")
        if bb_lower is not None:
            indicators["bb_lower"] = float(bb_lower)
            if float(close) < float(bb_lower):
                reasons.append(f"Close {close:.6f} below BB lower {bb_lower:.6f} (stretched)")
                conditions_met += 1
            else:
                failed.append(f"Close {close:.6f} above BB lower {bb_lower:.6f}")

        # 3. RSI oversold + turning up (momentum exhaustion)
        rsi = daily.get("rsi_14")
        rsi_threshold = self.entry.get("rsi_oversold", 30)
        if rsi is not None:
            indicators["rsi_14"] = float(rsi)
            if rsi < rsi_threshold:
                # Check RSI slope (is it turning up?)
                rsi_prev = daily.get("rsi_14_prev")
                if rsi_prev is not None and float(rsi) > float(rsi_prev):
                    reasons.append(f"RSI {rsi:.1f} < {rsi_threshold} and turning up (exhaustion)")
                    conditions_met += 1
                else:
                    # Still oversold, even without slope confirmation, partial credit
                    reasons.append(f"RSI {rsi:.1f} < {rsi_threshold} (oversold)")
                    conditions_met += 0.75
            else:
                failed.append(f"RSI {rsi:.1f} >= {rsi_threshold}")

        # 4. ATR% low/stable — want a drift, not a crash
        atr = daily.get("atr_14")
        max_atr_pct = self.entry.get("max_atr_pct", 5.0)
        if atr is not None and float(close) > 0:
            atr_pct = float(atr) / float(close) * 100
            indicators["atr_pct"] = round(atr_pct, 2)
            if atr_pct < max_atr_pct:
                reasons.append(f"ATR% = {atr_pct:.1f}% < {max_atr_pct}% (stable volatility)")
                conditions_met += 1
            else:
                failed.append(f"ATR% = {atr_pct:.1f}% >= {max_atr_pct}% (too volatile — crash risk)")

        # Need at least 3 conditions (regime + stretch are mandatory)
        min_conditions = self.entry.get("min_conditions", 3)
        confidence = conditions_met / conditions_total if conditions_total > 0 else 0.0

        has_regime = any("Regime" in r for r in reasons)
        has_stretch = any("stretched" in r for r in reasons)
        side = "buy" if conditions_met >= min_conditions and has_regime and has_stretch else "none"

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

        # Hard stop loss
        stop_pct = self.exit.get("stop_loss_pct", 3.0)
        if pnl_pct <= -stop_pct:
            return Signal(
                side="sell", confidence=1.0,
                reasons=[f"Hard stop: {pnl_pct:.1f}% <= -{stop_pct}%"],
            )

        # Primary target: price reaches SMA(20) — the "mean"
        sma_20 = daily.get("ema_20")  # Using EMA20 as proxy for SMA20
        if sma_20 is not None:
            if current_price >= float(sma_20):
                # Check volume — if high, hold to upper BB
                vol_ratio = daily.get("volume_ratio")
                bb_upper = daily.get("bb_upper")
                vol_spike_threshold = self.exit.get("vol_spike_threshold", 2.0)

                if vol_ratio is not None and vol_ratio > vol_spike_threshold and bb_upper is not None:
                    if current_price < float(bb_upper):
                        # Volume spike — hold for upper BB
                        return None
                    else:
                        return Signal(
                            side="sell", confidence=1.0,
                            reasons=[f"Upper BB reached with volume spike: {current_price:.6f} >= {bb_upper:.6f}"],
                        )

                return Signal(
                    side="sell", confidence=0.9,
                    reasons=[f"Mean reached: {current_price:.6f} >= SMA20 {sma_20:.6f} (PnL {pnl_pct:+.1f}%)"],
                )

        # Time stop (passed via daily dict)
        max_hold_days = self.exit.get("max_hold_days", 2)
        days_held = daily.get("days_held", 0)
        if days_held >= max_hold_days and pnl_pct <= 0:
            return Signal(
                side="sell", confidence=0.8,
                reasons=[f"Time stop: held {days_held} days, no profit ({pnl_pct:+.1f}%)"],
            )

        return None
