"""Abstract base for trading strategies.

All strategies implement evaluate_signal() — used by both live signal scanner
and backtester (same logic, different data source).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Signal:
    """Output of strategy evaluation."""
    side: str  # 'buy', 'sell', or 'none'
    confidence: float  # 0.0 - 1.0
    reasons: list[str] = field(default_factory=list)
    failed_conditions: list[str] = field(default_factory=list)
    indicators: dict[str, float] = field(default_factory=dict)

    @property
    def has_signal(self) -> bool:
        return self.side in ("buy", "sell") and self.confidence >= 0.50


class BaseStrategy(ABC):
    """Abstract strategy interface."""

    name: str
    strategy_type: str

    def __init__(self, params: dict) -> None:
        self.params = params
        self.entry = params.get("entry", {})
        self.exit = params.get("exit", {})
        self.position = params.get("position", {})

    @abstractmethod
    def evaluate_signal(self, daily: dict, intraday: dict | None = None) -> Signal:
        """Evaluate entry/exit conditions against current indicators.

        Args:
            daily: Latest daily indicators (from indicators_daily)
            intraday: Latest intraday indicators (from indicators_intraday), may be None

        Returns:
            Signal with side, confidence, reasons
        """

    def should_exit(self, entry_price: float, current_price: float, daily: dict) -> Signal | None:
        """Check exit conditions (stop-loss, take-profit, signal exit).

        Returns Signal(side='sell') if should exit, None otherwise.
        """
        tp_pct = self.exit.get("take_profit_pct", 0)
        sl_pct = self.exit.get("stop_loss_pct", 0)

        if entry_price <= 0:
            return None

        pnl_pct = (current_price - entry_price) / entry_price * 100

        # Take profit
        if tp_pct > 0 and pnl_pct >= tp_pct:
            return Signal(
                side="sell", confidence=1.0,
                reasons=[f"Take profit: {pnl_pct:.1f}% >= {tp_pct}%"],
            )

        # Stop loss
        if sl_pct > 0 and pnl_pct <= -sl_pct:
            return Signal(
                side="sell", confidence=1.0,
                reasons=[f"Stop loss: {pnl_pct:.1f}% <= -{sl_pct}%"],
            )

        return None
