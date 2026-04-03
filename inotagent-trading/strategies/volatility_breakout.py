"""Volatility Breakout strategy — "The Scout"

Catches moves at the very start by detecting volatility squeezes
(BB inside Keltner Channels) then entering on the breakout.

Entry conditions:
1. Squeeze: BB(20,2) inside Keltner(20,1.5)
2. Breakout: price > upper BB AND > 20-day high
3. ADX < 20 (trend hasn't started yet — catching first candle)
4. RVOL > 2.0 (volume confirms institutional participation)

Exit:
- Stop loss: entry - (1.5 × ATR)
- Trail: 8-day EMA (exit when close drops below)
- Time stop: exit after N days if not in profit

Small position size (5%) due to higher false breakout risk.
"""

from __future__ import annotations

from strategies.base import BaseStrategy, Signal


class VolatilityBreakoutStrategy(BaseStrategy):
    name = "volatility_breakout"
    strategy_type = "volatility_breakout"

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

        # 1. Squeeze: BB inside Keltner
        squeeze = daily.get("squeeze")
        if squeeze is not None:
            indicators["squeeze"] = float(squeeze)
            if squeeze > 0:
                reasons.append("Squeeze detected: BB inside Keltner Channels")
                conditions_met += 1
            else:
                failed.append("No squeeze: BB outside Keltner")
        else:
            # If squeeze not computed, check BB width as proxy
            bb_width = daily.get("bb_width")
            if bb_width is not None:
                indicators["bb_width"] = float(bb_width)
                max_width = self.entry.get("max_bb_width_squeeze", 3.0)
                if bb_width < max_width:
                    reasons.append(f"Low BB width {bb_width:.1f}% < {max_width}% (squeeze proxy)")
                    conditions_met += 1
                else:
                    failed.append(f"BB width {bb_width:.1f}% >= {max_width}%")

        # 2. Breakout: close > upper BB AND > 20-day high
        bb_upper = daily.get("bb_upper")
        high_20d = daily.get("high_20d")
        breakout_met = False

        if bb_upper is not None:
            indicators["bb_upper"] = float(bb_upper)
            if float(close) > float(bb_upper):
                if high_20d is not None:
                    indicators["high_20d"] = float(high_20d)
                    if float(close) > float(high_20d):
                        reasons.append(f"Breakout: price > BB upper + 20d high")
                        breakout_met = True
                    else:
                        failed.append(f"Price > BB upper but <= 20d high")
                else:
                    reasons.append(f"Breakout: price > BB upper")
                    breakout_met = True
            else:
                failed.append(f"No breakout: price {close:.6f} <= BB upper {bb_upper:.6f}")

        if breakout_met:
            conditions_met += 1

        # 3. ADX < threshold (trend hasn't started)
        adx = daily.get("adx_14")
        adx_threshold = self.entry.get("adx_threshold", 20)
        if adx is not None:
            indicators["adx_14"] = float(adx)
            if adx < adx_threshold:
                reasons.append(f"ADX {adx:.1f} < {adx_threshold} (trend not started)")
                conditions_met += 1
            else:
                failed.append(f"ADX {adx:.1f} >= {adx_threshold} (trend already in progress)")

        # 4. RVOL > min (volume confirmation)
        vol_ratio = daily.get("volume_ratio")
        min_rvol = self.entry.get("rvol_min", 2.0)
        if vol_ratio is not None:
            indicators["volume_ratio"] = float(vol_ratio)
            if vol_ratio > min_rvol:
                reasons.append(f"RVOL {vol_ratio:.1f} > {min_rvol} (institutional volume)")
                conditions_met += 1
            else:
                failed.append(f"RVOL {vol_ratio:.1f} <= {min_rvol} (low volume)")

        # Need at least 3 of 4 conditions (squeeze is the most important)
        min_conditions = self.entry.get("min_conditions", 3)
        confidence = conditions_met / conditions_total if conditions_total > 0 else 0.0

        has_squeeze = any("Squeeze" in r or "squeeze" in r for r in reasons)
        side = "buy" if conditions_met >= min_conditions and has_squeeze else "none"

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

        atr = daily.get("atr_14")
        pnl_pct = (current_price - entry_price) / entry_price * 100

        # Stop loss: entry - (1.5 × ATR)
        stop_mult = self.exit.get("stop_atr_mult", 1.5)
        if atr is not None:
            stop_price = entry_price - (stop_mult * float(atr))
            if current_price <= stop_price:
                return Signal(
                    side="sell", confidence=1.0,
                    reasons=[f"Stop loss: {current_price:.6f} <= {stop_price:.6f} (ATR×{stop_mult})"],
                )

        # Trail via 8-day EMA
        ema_8 = daily.get("ema_8")
        if ema_8 is not None and pnl_pct > 0:
            if current_price < float(ema_8):
                return Signal(
                    side="sell", confidence=0.9,
                    reasons=[f"EMA(8) trail: price {current_price:.6f} < EMA8 {ema_8:.6f} (PnL {pnl_pct:+.1f}%)"],
                )

        # Time stop (checked externally — backtester passes days_held)
        time_stop_days = self.exit.get("time_stop_days", 3)
        days_held = daily.get("days_held", 0)
        if days_held >= time_stop_days and pnl_pct <= 0:
            return Signal(
                side="sell", confidence=0.8,
                reasons=[f"Time stop: held {days_held} days with no profit ({pnl_pct:+.1f}%)"],
            )

        return None
