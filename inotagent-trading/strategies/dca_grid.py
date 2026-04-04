"""DCA Grid strategy — Batch Grid and Adaptive FIFO Grid modes.

Unlike signal-based strategies, the grid manages a CYCLE of multiple limit orders.
It doesn't produce buy/sell signals — it computes grid levels, places orders,
and manages the take-profit/stop-loss lifecycle.

Two modes:
- Batch Grid: one TP sell for all filled levels at weighted avg + target
- Adaptive FIFO Grid: per-level independent TP sells + mid-cycle sentiment adjustment
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal


@dataclass
class GridLevel:
    """One level in the grid."""
    level: int                          # 1 = shallowest, 5 = deepest
    price: Decimal                      # limit buy price
    capital: Decimal                    # USD allocated to this level
    quantity: Decimal = Decimal("0")    # filled quantity (computed from capital / price)
    status: str = "open"               # open, filled, cancelled, sold
    buy_order_id: int | None = None    # DB order id
    sell_order_id: int | None = None   # DB order id (FIFO mode: per-level TP)
    tp_price: Decimal | None = None    # take-profit price (FIFO mode)
    exchange_buy_id: str | None = None
    exchange_sell_id: str | None = None


@dataclass
class GridCycle:
    """Complete state of a grid cycle."""
    cycle_id: str
    asset_symbol: str
    venue_code: str
    mode: str                           # "batch" or "adaptive_fifo"
    levels: list[GridLevel]
    stop_loss_price: Decimal
    stop_loss_exchange_id: str | None = None
    # Batch mode
    avg_entry: Decimal | None = None
    take_profit_price: Decimal | None = None
    take_profit_order_id: int | None = None
    exchange_tp_id: str | None = None
    # State
    status: str = "active"              # active, transition_pending, expired_pending, closed
    sentiment_at_open: float = 0.0
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: datetime | None = None
    close_reason: str | None = None

    @property
    def filled_levels(self) -> list[GridLevel]:
        return [l for l in self.levels if l.status == "filled"]

    @property
    def open_levels(self) -> list[GridLevel]:
        return [l for l in self.levels if l.status == "open"]

    @property
    def total_filled_capital(self) -> Decimal:
        return sum(l.capital for l in self.filled_levels)

    @property
    def total_filled_quantity(self) -> Decimal:
        return sum(l.quantity for l in self.filled_levels)

    @property
    def weighted_avg_entry(self) -> Decimal | None:
        filled = self.filled_levels
        if not filled:
            return None
        total_cost = sum(l.capital for l in filled)
        total_qty = sum(l.quantity for l in filled)
        if total_qty == 0:
            return None
        return total_cost / total_qty

    def to_json(self) -> dict:
        return {
            "cycle_id": self.cycle_id,
            "asset": self.asset_symbol,
            "venue": self.venue_code,
            "mode": self.mode,
            "status": self.status,
            "levels": [
                {
                    "level": l.level,
                    "price": float(l.price),
                    "capital": float(l.capital),
                    "quantity": float(l.quantity),
                    "status": l.status,
                    "buy_order_id": l.buy_order_id,
                    "sell_order_id": l.sell_order_id,
                    "tp_price": float(l.tp_price) if l.tp_price else None,
                }
                for l in self.levels
            ],
            "stop_loss_price": float(self.stop_loss_price),
            "avg_entry": float(self.avg_entry) if self.avg_entry else None,
            "take_profit_price": float(self.take_profit_price) if self.take_profit_price else None,
            "sentiment_at_open": self.sentiment_at_open,
            "opened_at": self.opened_at.isoformat(),
            "status": self.status,
        }


def get_volatility_regime(atr_pct: float) -> str:
    """Classify current volatility."""
    if atr_pct < 2.0:
        return "low"
    elif atr_pct < 4.0:
        return "normal"
    elif atr_pct < 6.0:
        return "high"
    return "extreme"


def get_grid_params(volatility: str, params: dict) -> tuple[float, float]:
    """Get ATR multiplier and profit target for volatility regime."""
    regimes = params.get("grid", {}).get("volatility_regimes", {})
    defaults = {"low": (0.4, 1.0), "normal": (0.5, 1.5), "high": (0.7, 2.5)}

    if volatility in regimes:
        r = regimes[volatility]
        return r.get("atr_mult", defaults[volatility][0]), r.get("profit_target", defaults[volatility][1])

    return defaults.get(volatility, (0.5, 1.5))


def compute_grid_levels(
    current_price: Decimal,
    atr: Decimal,
    capital_for_cycle: Decimal,
    params: dict,
    maker_fee: Decimal = Decimal("0.0024"),
) -> tuple[list[GridLevel], Decimal, float]:
    """Compute grid levels, stop-loss price, and profit target.

    Returns (levels, stop_loss_price, profit_target_pct)
    """
    atr_pct = float(atr / current_price * 100)
    volatility = get_volatility_regime(atr_pct)

    if volatility == "extreme":
        return [], Decimal("0"), 0.0

    atr_mult, profit_target = get_grid_params(volatility, params)

    grid_spacing_pct = Decimal(str(atr_pct * atr_mult / 100))

    num_levels = params.get("grid", {}).get("num_levels", 5)
    weights = params.get("grid", {}).get("weights", [1, 1, 2, 3, 3])
    if len(weights) < num_levels:
        weights = weights + [1] * (num_levels - len(weights))
    total_weight = sum(weights[:num_levels])

    levels = []
    for i in range(num_levels):
        level_num = i + 1
        price = current_price * (1 - grid_spacing_pct * level_num)
        weight = weights[i]
        level_capital = capital_for_cycle * Decimal(str(weight)) / Decimal(str(total_weight))

        # Compute quantity (fee-adjusted)
        quantity = level_capital / (price * (1 + maker_fee))

        levels.append(GridLevel(
            level=level_num,
            price=price.quantize(Decimal("0.00000001")),
            capital=level_capital.quantize(Decimal("0.01")),
            quantity=quantity.quantize(Decimal("0.00000001")),
        ))

    # Stop-loss: one spacing below deepest level
    deepest_price = levels[-1].price
    stop_loss = deepest_price * (1 - grid_spacing_pct)

    return levels, stop_loss.quantize(Decimal("0.00000001")), profit_target


def compute_batch_tp_price(
    filled_levels: list[GridLevel],
    profit_target_pct: float,
    maker_fee: Decimal = Decimal("0.0024"),
) -> Decimal | None:
    """Compute take-profit price for Batch mode (weighted avg + target + fees)."""
    if not filled_levels:
        return None

    total_cost = sum(l.capital for l in filled_levels)
    total_qty = sum(l.quantity for l in filled_levels)
    if total_qty == 0:
        return None

    avg_entry = total_cost / total_qty
    tp = avg_entry * (1 + Decimal(str(profit_target_pct / 100)) + maker_fee)
    return tp.quantize(Decimal("0.00000001"))


def compute_fifo_tp_price(
    level: GridLevel,
    profit_target_pct: float,
    maker_fee: Decimal = Decimal("0.0024"),
) -> Decimal:
    """Compute take-profit price for a single FIFO level."""
    tp = level.price * (1 + Decimal(str(profit_target_pct / 100)) + maker_fee)
    return tp.quantize(Decimal("0.00000001"))


def should_open_cycle(
    regime_score: float,
    rsi: float | None,
    atr_pct: float,
    has_active_cycle: bool,
    expired_pending_count: int,
    params: dict,
) -> tuple[bool, str | None, bool]:
    """Check if a new grid cycle should open.

    Returns (should_open, reason_if_not, is_defensive).
    Defensive mode: when normal entry fails but RSI is deeply oversold — opens wider, safer grid.
    """
    mode_params = params.get("mode", {})
    entry_params = params.get("entry", {})
    exit_params = params.get("exit", {})

    pause_threshold = mode_params.get("regime_pause_threshold", 65)
    max_expired = exit_params.get("max_expired_pending_per_asset", 2)

    # Hard blocks — no override even in defensive mode
    if regime_score >= pause_threshold:
        return False, f"Regime {regime_score:.0f} >= {pause_threshold} (grid paused, trend active)", False

    if has_active_cycle:
        return False, "Active cycle already open", False

    if expired_pending_count >= max_expired:
        return False, f"Max expired_pending cycles reached ({expired_pending_count}/{max_expired})", False

    volatility = get_volatility_regime(atr_pct)
    if volatility == "extreme":
        return False, "Extreme volatility — no grid entry", False

    # Normal entry check
    rsi_max = entry_params.get("rsi_entry_max", 60)
    max_atr = entry_params.get("max_atr_pct", 6.0)

    normal_pass = True
    normal_reason = None

    if rsi is not None and rsi > rsi_max:
        normal_pass = False
        normal_reason = f"RSI {rsi:.1f} > {rsi_max} (overbought)"

    if atr_pct >= max_atr:
        normal_pass = False
        normal_reason = f"ATR% {atr_pct:.1f} >= {max_atr} (too volatile)"

    if normal_pass:
        return True, None, False

    # Normal entry failed — check defensive mode
    defensive_enabled = entry_params.get("defensive_mode_enabled", False)
    defensive_rsi = entry_params.get("defensive_rsi_oversold", 30)

    if defensive_enabled and rsi is not None and rsi < defensive_rsi:
        return True, None, True  # defensive mode activated

    return False, normal_reason, False


def select_grid_mode(regime_score: float, params: dict) -> str:
    """Auto-select grid mode based on regime score."""
    mode_params = params.get("mode", {})
    batch_max = mode_params.get("batch_regime_max", 30)

    if regime_score < batch_max:
        return "batch"
    return "adaptive_fifo"


def create_cycle(
    asset_symbol: str,
    venue_code: str,
    current_price: Decimal,
    atr: Decimal,
    capital_for_cycle: Decimal,
    regime_score: float,
    params: dict,
    sentiment_score: float = 0.0,
    maker_fee: Decimal = Decimal("0.0024"),
    defensive: bool = False,
) -> GridCycle | None:
    """Create a new grid cycle with computed levels. Returns None if conditions fail.

    If defensive=True, uses wider spacing, higher profit target, equal weights.
    """
    if defensive:
        # Override grid params for defensive mode
        params = dict(params)
        params["grid"] = dict(params.get("grid", {}))
        params["grid"]["volatility_regimes"] = {
            "low": {"atr_mult": 0.8, "profit_target": 2.5},
            "normal": {"atr_mult": 0.8, "profit_target": 2.5},
            "high": {"atr_mult": 0.8, "profit_target": 2.5},
        }
        params["grid"]["weights"] = [1, 1, 1, 1, 1]  # equal, conservative

    levels, stop_loss, profit_target = compute_grid_levels(
        current_price, atr, capital_for_cycle, params, maker_fee
    )

    if not levels:
        return None

    mode = select_grid_mode(regime_score, params)

    cycle = GridCycle(
        cycle_id=f"grid-{asset_symbol.lower()}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
        asset_symbol=asset_symbol,
        venue_code=venue_code,
        mode=mode,
        levels=levels,
        stop_loss_price=stop_loss,
        sentiment_at_open=sentiment_score,
    )

    return cycle
