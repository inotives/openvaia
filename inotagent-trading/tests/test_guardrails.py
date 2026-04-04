"""Tests for trading guardrails."""

import sys
from decimal import Decimal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from guardrails import DEFAULTS, validate_order

# Test uses DEFAULTS as the operational config (no DB in tests)
ALLOWED_PAIRS = ["CRO/USDT"]
MAX_POSITION_PCT = DEFAULTS["max_position_pct"]
MAX_DAILY_LOSS_PCT = DEFAULTS["max_daily_loss_pct"]
MAX_OPEN_POSITIONS = DEFAULTS["max_open_positions"]
MAX_STOP_LOSS_PCT = DEFAULTS["max_stop_loss_pct"]
MIN_TRADE_SIZE_USD = DEFAULTS["min_trade_size_usd"]


def _valid_order(**overrides):
    """Helper — returns kwargs for a valid buy order."""
    defaults = {
        "pair_symbol": "CRO/USDT",
        "side": "buy",
        "amount_usd": Decimal("50"),
        "portfolio_value_usd": Decimal("1000"),
        "open_position_count": 0,
        "daily_pnl_pct": Decimal("0"),
        "stop_loss_pct": Decimal("0.05"),
        "allowed_pairs": ALLOWED_PAIRS,
    }
    defaults.update(overrides)
    return defaults


class TestGuardrailsPass:
    def test_valid_buy_passes(self):
        result = validate_order(**_valid_order())
        assert result.passed
        assert result.violations == []
        assert not result.needs_human_approval

    def test_valid_sell_no_stop_loss_needed(self):
        result = validate_order(**_valid_order(side="sell", stop_loss_pct=None))
        assert result.passed

    def test_sell_ignores_max_positions(self):
        result = validate_order(**_valid_order(side="sell", open_position_count=5))
        assert result.passed

    def test_snapshot_captures_values(self):
        result = validate_order(**_valid_order())
        snap = result.snapshot
        assert snap["max_position_pct"] == float(MAX_POSITION_PCT)
        assert "max_open_positions" in snap


class TestGuardrailsFail:
    def test_disallowed_pair(self):
        result = validate_order(**_valid_order(pair_symbol="DOGE/USDT"))
        assert not result.passed
        assert any("not in active" in v for v in result.violations)

    def test_below_min_trade_size(self):
        result = validate_order(**_valid_order(amount_usd=Decimal("1")))
        assert not result.passed
        assert any("minimum" in v for v in result.violations)

    def test_exceeds_position_size(self):
        result = validate_order(**_valid_order(amount_usd=Decimal("150")))
        assert not result.passed
        assert any("exceeds max" in v for v in result.violations)

    def test_max_open_positions(self):
        result = validate_order(**_valid_order(open_position_count=3))
        assert not result.passed
        assert any("open positions" in v for v in result.violations)

    def test_daily_loss_exceeded(self):
        result = validate_order(**_valid_order(daily_pnl_pct=Decimal("-0.06")))
        assert not result.passed
        assert any("Daily loss" in v for v in result.violations)

    def test_stop_loss_required(self):
        result = validate_order(**_valid_order(stop_loss_pct=None))
        assert not result.passed
        assert any("Stop-loss is required" in v for v in result.violations)

    def test_stop_loss_too_wide(self):
        result = validate_order(**_valid_order(stop_loss_pct=Decimal("0.10")))
        assert not result.passed
        assert any("wider than max" in v for v in result.violations)

    def test_multiple_violations(self):
        result = validate_order(**_valid_order(
            pair_symbol="DOGE/USDT",
            amount_usd=Decimal("1"),
            stop_loss_pct=None,
        ))
        assert not result.passed
        assert len(result.violations) >= 3


class TestHumanApproval:
    def test_large_trade_needs_approval(self):
        result = validate_order(**_valid_order(amount_usd=Decimal("250")))
        # 250/1000 = 25% > 20% threshold — needs approval but also fails position size
        assert result.needs_human_approval

    def test_normal_trade_no_approval(self):
        result = validate_order(**_valid_order(amount_usd=Decimal("50")))
        assert not result.needs_human_approval


class TestEdgeCases:
    def test_zero_portfolio_value(self):
        result = validate_order(**_valid_order(portfolio_value_usd=Decimal("0")))
        # Should still pass — position % check skipped when portfolio is 0
        assert result.passed

    def test_exact_min_trade_size(self):
        result = validate_order(**_valid_order(amount_usd=MIN_TRADE_SIZE_USD))
        assert result.passed

    def test_exact_max_stop_loss(self):
        result = validate_order(**_valid_order(stop_loss_pct=MAX_STOP_LOSS_PCT))
        assert result.passed

    def test_exact_daily_loss_limit(self):
        result = validate_order(**_valid_order(daily_pnl_pct=-MAX_DAILY_LOSS_PCT))
        # At exactly the limit, not exceeded
        assert result.passed

    def test_multi_pair_allowed(self):
        """Multiple pairs from DB — all should pass."""
        multi_pairs = ["CRO/USDT", "BTC/USDT", "ETH/USDT"]
        for pair in multi_pairs:
            result = validate_order(**_valid_order(pair_symbol=pair, allowed_pairs=multi_pairs))
            assert result.passed, f"{pair} should be allowed"

    def test_no_allowed_pairs_skips_check(self):
        """If allowed_pairs is None, pair check is skipped."""
        result = validate_order(**_valid_order(pair_symbol="DOGE/USDT", allowed_pairs=None))
        assert result.passed  # No pair violation when check is skipped


class TestCeilingEnforcement:
    def test_db_cannot_exceed_hard_ceiling(self):
        """DB config with extreme values gets clamped to hard ceilings."""
        from guardrails import HARD_MAX_POSITION_PCT, _enforce_ceilings
        extreme_config = {
            "max_position_pct": Decimal("0.99"),  # 99% — way above ceiling
            "max_daily_loss_pct": Decimal("0.50"),
            "max_open_positions": 100,
            "max_stop_loss_pct": Decimal("0.50"),
            "min_trade_size_usd": Decimal("0.01"),  # below floor
            "human_approval_threshold": Decimal("0.99"),
        }
        clamped = _enforce_ceilings(extreme_config)
        assert clamped["max_position_pct"] == HARD_MAX_POSITION_PCT
        assert clamped["max_open_positions"] == 10
        assert clamped["max_stop_loss_pct"] == Decimal("0.15")
        assert clamped["min_trade_size_usd"] == Decimal("1.0")
        assert clamped["human_approval_threshold"] == Decimal("0.50")

    def test_db_within_ceiling_passes_through(self):
        """DB config within bounds is used as-is."""
        from guardrails import _enforce_ceilings
        normal_config = {
            "max_position_pct": Decimal("0.15"),
            "max_daily_loss_pct": Decimal("0.03"),
            "max_open_positions": 5,
            "max_stop_loss_pct": Decimal("0.10"),
            "min_trade_size_usd": Decimal("10.0"),
            "human_approval_threshold": Decimal("0.30"),
        }
        clamped = _enforce_ceilings(normal_config)
        assert clamped == normal_config  # No changes

    def test_custom_config_used_in_validation(self):
        """Passing custom config changes the effective limits."""
        relaxed = dict(DEFAULTS)
        relaxed["max_position_pct"] = Decimal("0.20")
        # 150/1000 = 15% — would fail with default 10% but passes with 20%
        result = validate_order(**_valid_order(amount_usd=Decimal("150"), config=relaxed))
        assert result.passed

    def test_snapshot_captures_effective_config(self):
        """Snapshot should reflect the actual limits used (after ceiling enforcement)."""
        result = validate_order(**_valid_order())
        snap = result.snapshot
        assert snap["max_position_pct"] == float(DEFAULTS["max_position_pct"])
        assert snap["max_open_positions"] == DEFAULTS["max_open_positions"]
