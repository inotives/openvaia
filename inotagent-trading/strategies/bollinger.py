"""Bollinger Band Mean Reversion strategy.

Entry: price touches/crosses below lower band + RSI confirmation
Exit: price reaches middle band (SMA20) or upper band, or stop-loss

Works best in ranging/choppy markets where momentum strategy struggles.
"""

from __future__ import annotations

from strategies.base import BaseStrategy, Signal


class BollingerStrategy(BaseStrategy):
    name = "bollinger"
    strategy_type = "bollinger"

    def evaluate_signal(self, daily: dict, intraday: dict | None = None) -> Signal:
        reasons = []
        failed = []
        indicators = {}
        weights_met = 0.0
        weights_total = 0.0

        condition_weights = self.entry.get("condition_weights", {})

        close = daily.get("close")
        if close is None:
            return Signal(side="none", confidence=0.0, failed_conditions=["No close price"])

        indicators["close"] = float(close)

        # BB lower touch
        bb_lower = daily.get("bb_lower")
        w = condition_weights.get("bb_lower", 3)
        weights_total += w
        if bb_lower is not None:
            indicators["bb_lower"] = float(bb_lower)
            bb_margin = self.entry.get("bb_lower_margin_pct", 1.0) / 100
            threshold = float(bb_lower) * (1 + bb_margin)
            if float(close) <= threshold:
                reasons.append(f"Close {close:.6f} near/below BB lower {bb_lower:.6f}")
                weights_met += w
            else:
                failed.append(f"Close {close:.6f} above BB lower {bb_lower:.6f}")

        # RSI oversold confirmation
        rsi = daily.get("rsi_14")
        rsi_threshold = self.entry.get("rsi_threshold", 40)
        w = condition_weights.get("rsi", 2)
        weights_total += w
        if rsi is not None:
            indicators["rsi_14"] = float(rsi)
            if rsi < rsi_threshold:
                reasons.append(f"RSI(14) = {rsi:.1f} < {rsi_threshold} (oversold)")
                weights_met += w
            else:
                failed.append(f"RSI(14) = {rsi:.1f} >= {rsi_threshold}")

        # BB width (volatility filter — avoid buying in extreme compression)
        bb_width = daily.get("bb_width")
        min_bb_width = self.entry.get("min_bb_width", 2.0)
        w = condition_weights.get("bb_width", 1)
        weights_total += w
        if bb_width is not None:
            indicators["bb_width"] = float(bb_width)
            if bb_width > min_bb_width:
                reasons.append(f"BB width = {bb_width:.1f}% > {min_bb_width}% (sufficient volatility)")
                weights_met += w
            else:
                failed.append(f"BB width = {bb_width:.1f}% <= {min_bb_width}% (too compressed)")

        # Volume confirmation
        vol_ratio = daily.get("volume_ratio")
        min_vol = self.entry.get("volume_ratio_min", 0.8)
        w = condition_weights.get("volume", 1)
        weights_total += w
        if vol_ratio is not None:
            indicators["volume_ratio"] = float(vol_ratio)
            if vol_ratio > min_vol:
                reasons.append(f"Volume ratio = {vol_ratio:.1f} > {min_vol}")
                weights_met += w
            else:
                failed.append(f"Volume ratio = {vol_ratio:.1f} <= {min_vol}")

        confidence = weights_met / weights_total if weights_total > 0 else 0.0
        side = "buy" if confidence >= 0.50 and len(reasons) > 0 else "none"

        return Signal(
            side=side,
            confidence=round(confidence, 4),
            reasons=reasons,
            failed_conditions=failed,
            indicators=indicators,
        )

    def should_exit(self, entry_price: float, current_price: float, daily: dict) -> Signal | None:
        """Exit at middle band, upper band, or stop-loss."""
        # Stop-loss first
        sl_pct = self.exit.get("stop_loss_pct", 5.0)
        if entry_price > 0:
            pnl_pct = (current_price - entry_price) / entry_price * 100
            if pnl_pct <= -sl_pct:
                return Signal(
                    side="sell", confidence=1.0,
                    reasons=[f"Stop loss: {pnl_pct:.1f}% <= -{sl_pct}%"],
                )

        # Exit at middle band (SMA20 = bb middle)
        bb_upper = daily.get("bb_upper")
        bb_lower = daily.get("bb_lower")
        if bb_upper is not None and bb_lower is not None:
            bb_mid = (float(bb_upper) + float(bb_lower)) / 2

            exit_target = self.exit.get("exit_target", "middle")  # middle or upper
            if exit_target == "upper" and current_price >= float(bb_upper):
                return Signal(
                    side="sell", confidence=1.0,
                    reasons=[f"Price {current_price:.6f} reached BB upper {bb_upper:.6f}"],
                )
            elif exit_target == "middle" and current_price >= bb_mid:
                return Signal(
                    side="sell", confidence=1.0,
                    reasons=[f"Price {current_price:.6f} reached BB middle {bb_mid:.6f}"],
                )

        # Fallback: take profit
        tp_pct = self.exit.get("take_profit_pct", 0)
        if tp_pct > 0 and entry_price > 0:
            pnl_pct = (current_price - entry_price) / entry_price * 100
            if pnl_pct >= tp_pct:
                return Signal(
                    side="sell", confidence=1.0,
                    reasons=[f"Take profit: {pnl_pct:.1f}% >= {tp_pct}%"],
                )

        return None
