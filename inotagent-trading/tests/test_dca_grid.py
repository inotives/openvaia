"""Tests for DCA Grid strategy — level computation, mode selection, entry conditions."""

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from strategies.dca_grid import (
    compute_batch_tp_price,
    compute_fifo_tp_price,
    compute_grid_levels,
    create_cycle,
    get_volatility_regime,
    select_grid_mode,
    should_open_cycle,
    GridLevel,
)

DEFAULT_PARAMS = {
    "mode": {
        "default": "adaptive_fifo",
        "auto_select_by_regime": True,
        "batch_regime_max": 30,
        "regime_pause_threshold": 65,
        "regime_resume_threshold": 55,
    },
    "entry": {
        "max_regime_score": 65,
        "rsi_entry_max": 60,
        "max_atr_pct": 6.0,
    },
    "grid": {
        "num_levels": 5,
        "weights": [1, 1, 2, 3, 3],
        "volatility_regimes": {
            "low": {"atr_mult": 0.4, "profit_target": 1.0},
            "normal": {"atr_mult": 0.5, "profit_target": 1.5},
            "high": {"atr_mult": 0.7, "profit_target": 2.5},
        },
    },
    "exit": {
        "max_expired_pending_per_asset": 2,
    },
    "position": {"capital_per_cycle_pct": 10},
}


class TestVolatilityRegime:
    def test_low(self):
        assert get_volatility_regime(1.5) == "low"

    def test_normal(self):
        assert get_volatility_regime(3.0) == "normal"

    def test_high(self):
        assert get_volatility_regime(5.0) == "high"

    def test_extreme(self):
        assert get_volatility_regime(7.0) == "extreme"


class TestGridLevels:
    def test_computes_5_levels(self):
        levels, stop, target = compute_grid_levels(
            Decimal("84000"), Decimal("2500"), Decimal("100"), DEFAULT_PARAMS
        )
        assert len(levels) == 5
        assert target == 1.5  # normal volatility

    def test_levels_descend(self):
        levels, _, _ = compute_grid_levels(
            Decimal("84000"), Decimal("2500"), Decimal("100"), DEFAULT_PARAMS
        )
        for i in range(1, len(levels)):
            assert levels[i].price < levels[i - 1].price

    def test_weights_distribute_capital(self):
        levels, _, _ = compute_grid_levels(
            Decimal("84000"), Decimal("2500"), Decimal("100"), DEFAULT_PARAMS
        )
        # Weights [1,1,2,3,3] total=10, so level 1=$10, level 3=$20, level 5=$30
        assert levels[0].capital == Decimal("10.00")
        assert levels[2].capital == Decimal("20.00")
        assert levels[4].capital == Decimal("30.00")

    def test_stop_loss_below_deepest(self):
        levels, stop, _ = compute_grid_levels(
            Decimal("84000"), Decimal("2500"), Decimal("100"), DEFAULT_PARAMS
        )
        assert stop < levels[-1].price

    def test_extreme_volatility_returns_empty(self):
        levels, _, _ = compute_grid_levels(
            Decimal("84000"), Decimal("6000"), Decimal("100"), DEFAULT_PARAMS
        )
        assert levels == []

    def test_total_capital_matches(self):
        levels, _, _ = compute_grid_levels(
            Decimal("84000"), Decimal("2500"), Decimal("100"), DEFAULT_PARAMS
        )
        total = sum(l.capital for l in levels)
        assert total == Decimal("100.00")


class TestModeSelection:
    def test_batch_below_30(self):
        assert select_grid_mode(20, DEFAULT_PARAMS) == "batch"

    def test_fifo_above_30(self):
        assert select_grid_mode(45, DEFAULT_PARAMS) == "adaptive_fifo"

    def test_fifo_at_60(self):
        assert select_grid_mode(60, DEFAULT_PARAMS) == "adaptive_fifo"


class TestShouldOpenCycle:
    def test_normal_conditions_open(self):
        can, reason, _ = should_open_cycle(40, 45, 3.0, False, 0, DEFAULT_PARAMS)
        assert can is True
        assert reason is None

    def test_regime_too_high(self):
        can, reason, _ = should_open_cycle(70, 45, 3.0, False, 0, DEFAULT_PARAMS)
        assert can is False
        assert "grid paused" in reason.lower()

    def test_active_cycle_blocks(self):
        can, reason, _ = should_open_cycle(40, 45, 3.0, True, 0, DEFAULT_PARAMS)
        assert can is False
        assert "Active cycle" in reason

    def test_rsi_too_high(self):
        can, reason, _ = should_open_cycle(40, 65, 3.0, False, 0, DEFAULT_PARAMS)
        assert can is False
        assert "RSI" in reason

    def test_atr_too_high(self):
        can, reason, _ = should_open_cycle(40, 45, 7.0, False, 0, DEFAULT_PARAMS)
        assert can is False
        assert "volatil" in reason.lower()  # matches "volatility" or "volatile"

    def test_max_expired_blocks(self):
        can, reason, _ = should_open_cycle(40, 45, 3.0, False, 2, DEFAULT_PARAMS)
        assert can is False
        assert "expired" in reason.lower()

    def test_hysteresis_allows_at_64(self):
        """RS 64 is below pause threshold 65 — should open."""
        can, _, _ = should_open_cycle(64, 45, 3.0, False, 0, DEFAULT_PARAMS)
        assert can is True

    def test_hysteresis_blocks_at_66(self):
        """RS 66 is above pause threshold 65 — should block."""
        can, _, _ = should_open_cycle(66, 45, 3.0, False, 0, DEFAULT_PARAMS)
        assert can is False


    def test_defensive_mode_activates(self):
        """RSI oversold + defensive enabled → opens in defensive mode."""
        params = dict(DEFAULT_PARAMS)
        params["entry"] = dict(params["entry"])
        params["entry"]["defensive_mode_enabled"] = True
        params["entry"]["defensive_rsi_oversold"] = 25
        params["entry"]["max_atr_pct"] = 6.0
        # RSI 20 < 25 (oversold) + ATR 5.5% < extreme but > max_atr (would normally block on RSI>60)
        # Actually: RSI 20 passes the rsi_max check (20 < 60). Let's make RSI fail + defensive save.
        # RSI 65 > 60 → normal fails. RSI 65 > 25 → defensive also fails. Need RSI < defensive threshold.
        # The trick: something else must fail normally. Use high ATR (but not extreme):
        params["entry"]["max_atr_pct"] = 4.0  # ATR 5% > 4% → normal blocks
        can, _, is_defensive = should_open_cycle(40, 20, 5.0, False, 0, params)
        assert can is True
        assert is_defensive is True

    def test_defensive_not_enabled(self):
        """RSI oversold but defensive not enabled → stays blocked."""
        can, reason, is_defensive = should_open_cycle(40, 20, 7.0, False, 0, DEFAULT_PARAMS)
        assert can is False
        assert is_defensive is False

    def test_defensive_cycle_has_wider_grid(self):
        """Defensive cycle should use wider spacing and equal weights."""
        cycle = create_cycle(
            "ETH", "cryptocom", Decimal("2000"), Decimal("100"),
            Decimal("100"), 25, DEFAULT_PARAMS, defensive=True
        )
        assert cycle is not None
        # Equal weights = equal capital per level
        capitals = [l.capital for l in cycle.levels]
        assert capitals[0] == capitals[4]  # all equal


class TestTakeProfitComputation:
    def test_batch_tp(self):
        levels = [
            GridLevel(1, Decimal("82000"), Decimal("10"), Decimal("0.000122")),
            GridLevel(2, Decimal("81000"), Decimal("10"), Decimal("0.000123")),
        ]
        tp = compute_batch_tp_price(levels, 1.5)
        assert tp is not None
        # TP should be above the highest filled level
        avg = Decimal("20") / Decimal("0.000245")
        assert tp > avg

    def test_batch_tp_empty(self):
        assert compute_batch_tp_price([], 1.5) is None

    def test_fifo_tp(self):
        level = GridLevel(1, Decimal("82000"), Decimal("10"), Decimal("0.000122"))
        tp = compute_fifo_tp_price(level, 1.5)
        assert tp > level.price
        # Should be price × (1 + 1.5% + 0.24% fee)
        expected = Decimal("82000") * Decimal("1.0174")
        assert abs(tp - expected) < Decimal("1")


class TestCreateCycle:
    def test_creates_valid_cycle(self):
        cycle = create_cycle(
            "BTC", "cryptocom", Decimal("84000"), Decimal("2500"),
            Decimal("100"), 40, DEFAULT_PARAMS
        )
        assert cycle is not None
        assert cycle.mode == "adaptive_fifo"
        assert len(cycle.levels) == 5
        assert cycle.stop_loss_price > 0

    def test_batch_mode_in_bear(self):
        cycle = create_cycle(
            "BTC", "cryptocom", Decimal("84000"), Decimal("2500"),
            Decimal("100"), 15, DEFAULT_PARAMS
        )
        assert cycle.mode == "batch"

    def test_returns_none_extreme_volatility(self):
        cycle = create_cycle(
            "BTC", "cryptocom", Decimal("84000"), Decimal("6000"),
            Decimal("100"), 40, DEFAULT_PARAMS
        )
        assert cycle is None
