"""Pyramid Trend strategy — scale into winners with asymmetric exits.

Entry: aggressive breakout (close > 20-day high + regime confirmation)
Pyramiding: add tranches at +5%, +12%, +20% from base entry
Exit: LIFO — newest lots have tight stops, base lot only exits on regime flip

Lot structure (of total allocation):
  Lot A: 40% — base position, exits on regime flip (RS < exit_regime)
  Lot B: 30% — added at +5%, exits on 15% trail or close < EMA50
  Lot C: 20% — added at +12%, exits on 7% trail or MACD cross down
  Lot D: 10% — added at +20%, exits on 3% trail or RSI > 80

Hard stop: all lots exit if price < Lot A entry (break-even protection).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from strategies.base import BaseStrategy, Signal


@dataclass
class PyramidLot:
    """Single lot in a pyramid position."""
    label: str            # A, B, C, D
    allocation_pct: float  # % of total allocation (40, 30, 20, 10)
    entry_price: float = 0.0
    quantity: float = 0.0
    is_open: bool = False
    highest_since_entry: float = 0.0
    entry_date: str = ""

    @property
    def cost_basis(self) -> float:
        return self.entry_price * self.quantity if self.is_open else 0.0


class PyramidTrendStrategy(BaseStrategy):
    name = "pyramid_trend"
    strategy_type = "pyramid_trend"

    def evaluate_signal(self, daily: dict, intraday: dict | None = None) -> Signal:
        """Evaluate entry for base lot (Lot A).

        Entry conditions:
        1. Close > 20-day high (breakout)
        2. Regime score >= min_regime_score
        3. EMA50 > EMA200 (golden cross)
        4. ADX >= min_adx
        5. RSI < rsi_max (not overbought)
        """
        reasons = []
        failed = []
        indicators = {}

        close = daily.get("close")
        if close is None:
            return Signal(side="none", confidence=0.0, failed_conditions=["No close price"])
        indicators["close"] = float(close)

        conditions_total = 5
        conditions_met = 0

        # 1. Breakout: close > 20-day high
        high_20d = daily.get("high_20d")
        if high_20d is not None:
            indicators["high_20d"] = float(high_20d)
            if float(close) > float(high_20d):
                reasons.append(f"Breakout: close > 20d high ({high_20d:.2f})")
                conditions_met += 1
            else:
                failed.append(f"No breakout: close <= 20d high ({high_20d:.2f})")
        else:
            # Fallback to 5-day high if 20d not available
            high_5d = daily.get("high_5d")
            if high_5d is not None and float(close) > float(high_5d):
                reasons.append(f"Breakout: close > 5d high (fallback)")
                conditions_met += 1
            else:
                failed.append("No breakout data")

        # 2. Regime score
        regime = daily.get("regime_score")
        min_regime = self.entry.get("min_regime_score", 50)
        if regime is not None:
            indicators["regime_score"] = float(regime)
            if regime >= min_regime:
                reasons.append(f"Regime {regime:.0f} >= {min_regime}")
                conditions_met += 1
            else:
                failed.append(f"Regime {regime:.0f} < {min_regime}")

        # 3. Golden cross: EMA50 > EMA200
        ema50 = daily.get("ema_50")
        ema200 = daily.get("ema_200")
        if ema50 is not None and ema200 is not None:
            indicators["ema_50"] = float(ema50)
            indicators["ema_200"] = float(ema200)
            if ema50 > ema200:
                reasons.append("EMA50 > EMA200 (golden cross)")
                conditions_met += 1
            else:
                failed.append("EMA50 <= EMA200 (death cross)")

        # 4. ADX strength
        adx = daily.get("adx_14")
        min_adx = self.entry.get("min_adx", 15)
        if adx is not None:
            indicators["adx_14"] = float(adx)
            if adx >= min_adx:
                reasons.append(f"ADX {adx:.1f} >= {min_adx}")
                conditions_met += 1
            else:
                failed.append(f"ADX {adx:.1f} < {min_adx}")

        # 5. RSI not overbought
        rsi = daily.get("rsi_14")
        rsi_max = self.entry.get("rsi_entry_max", 75)
        if rsi is not None:
            indicators["rsi_14"] = float(rsi)
            if rsi < rsi_max:
                reasons.append(f"RSI {rsi:.1f} < {rsi_max}")
                conditions_met += 1
            else:
                failed.append(f"RSI {rsi:.1f} >= {rsi_max} (overbought)")

        # Need at least 4 of 5 conditions
        min_conditions = self.entry.get("min_conditions", 4)
        confidence = conditions_met / conditions_total if conditions_total > 0 else 0.0
        side = "buy" if conditions_met >= min_conditions else "none"

        return Signal(
            side=side,
            confidence=round(confidence, 4),
            reasons=reasons,
            failed_conditions=failed,
            indicators=indicators,
        )

    def should_pyramid(self, lot_label: str, base_entry: float, current_price: float) -> bool:
        """Check if a pyramid lot should be added."""
        pyramid = self.params.get("pyramid", {})
        thresholds = pyramid.get("thresholds", {"B": 5.0, "C": 12.0, "D": 20.0})
        threshold = thresholds.get(lot_label)
        if threshold is None:
            return False
        gain_pct = (current_price - base_entry) / base_entry * 100
        return gain_pct >= threshold

    def should_exit_lot(
        self, lot: PyramidLot, current_price: float, daily: dict,
    ) -> Signal | None:
        """Check exit conditions for a specific lot. LIFO: D exits first, A last.

        Lot D: tight trail (3%) or RSI overbought
        Lot C: medium trail (7%) or MACD cross down
        Lot B: loose trail (15%) or close < EMA50
        Lot A: regime flip (RS < exit threshold)
        """
        if not lot.is_open or lot.entry_price <= 0:
            return None

        exit_params = self.params.get("exit", {})
        pnl_pct = (current_price - lot.entry_price) / lot.entry_price * 100

        if lot.label == "D":
            # Tight trailing stop
            trail_pct = exit_params.get("lot_d_trail_pct", 3.0)
            rsi_exit = exit_params.get("lot_d_rsi_exit", 80)
            # Trail from highest
            if lot.highest_since_entry > 0:
                drop_pct = (lot.highest_since_entry - current_price) / lot.highest_since_entry * 100
                if drop_pct >= trail_pct and pnl_pct > 0:
                    return Signal(
                        side="sell", confidence=1.0,
                        reasons=[f"Lot D trail: {drop_pct:.1f}% drop from high (PnL {pnl_pct:+.1f}%)"],
                    )
            # RSI overbought exit
            rsi = daily.get("rsi_14")
            if rsi is not None and rsi > rsi_exit:
                return Signal(
                    side="sell", confidence=0.9,
                    reasons=[f"Lot D RSI exit: {rsi:.1f} > {rsi_exit}"],
                )

        elif lot.label == "C":
            # Medium trailing stop
            trail_pct = exit_params.get("lot_c_trail_pct", 7.0)
            if lot.highest_since_entry > 0:
                drop_pct = (lot.highest_since_entry - current_price) / lot.highest_since_entry * 100
                if drop_pct >= trail_pct and pnl_pct > 0:
                    return Signal(
                        side="sell", confidence=1.0,
                        reasons=[f"Lot C trail: {drop_pct:.1f}% drop from high (PnL {pnl_pct:+.1f}%)"],
                    )
            # MACD cross down
            macd = daily.get("macd")
            macd_signal = daily.get("macd_signal")
            if macd is not None and macd_signal is not None and macd < macd_signal:
                macd_hist = daily.get("macd_hist")
                # Only exit on MACD cross if we're in profit
                if pnl_pct > 2.0:
                    return Signal(
                        side="sell", confidence=0.8,
                        reasons=[f"Lot C MACD cross down (PnL {pnl_pct:+.1f}%)"],
                    )

        elif lot.label == "B":
            # Loose trailing stop
            trail_pct = exit_params.get("lot_b_trail_pct", 15.0)
            if lot.highest_since_entry > 0:
                drop_pct = (lot.highest_since_entry - current_price) / lot.highest_since_entry * 100
                if drop_pct >= trail_pct:
                    return Signal(
                        side="sell", confidence=1.0,
                        reasons=[f"Lot B trail: {drop_pct:.1f}% drop from high (PnL {pnl_pct:+.1f}%)"],
                    )
            # Close below EMA50
            ema50 = daily.get("ema_50")
            if ema50 is not None and current_price < float(ema50) and pnl_pct > 0:
                return Signal(
                    side="sell", confidence=0.8,
                    reasons=[f"Lot B: price < EMA50 ({ema50:.2f}) (PnL {pnl_pct:+.1f}%)"],
                )

        elif lot.label == "A":
            # Regime flip — only exit when regime goes bearish
            exit_regime = exit_params.get("lot_a_exit_regime", 40)
            regime = daily.get("regime_score")
            if regime is not None and regime < exit_regime:
                return Signal(
                    side="sell", confidence=1.0,
                    reasons=[f"Lot A regime flip: RS {regime:.0f} < {exit_regime} (PnL {pnl_pct:+.1f}%)"],
                )
            # Also exit on extreme loss from high (catastrophic reversal protection)
            trail_pct = exit_params.get("lot_a_trail_pct", 25.0)
            if lot.highest_since_entry > 0:
                drop_pct = (lot.highest_since_entry - current_price) / lot.highest_since_entry * 100
                if drop_pct >= trail_pct:
                    return Signal(
                        side="sell", confidence=1.0,
                        reasons=[f"Lot A catastrophic trail: {drop_pct:.1f}% drop (PnL {pnl_pct:+.1f}%)"],
                    )

        return None

    def should_exit(self, entry_price: float, current_price: float, daily: dict) -> Signal | None:
        """Fallback for backtester compatibility — not used in pyramid mode."""
        return None

    def get_lot_allocations(self) -> dict[str, float]:
        """Get allocation percentages for each lot."""
        pyramid = self.params.get("pyramid", {})
        return pyramid.get("allocations", {"A": 40, "B": 30, "C": 20, "D": 10})
