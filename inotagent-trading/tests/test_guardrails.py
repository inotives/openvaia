"""Tests for trading guardrails."""

import sys
from decimal import Decimal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from guardrails import (
    ALLOWED_PAIRS,
    MAX_DAILY_LOSS_PCT,
    MAX_OPEN_POSITIONS,
    MAX_POSITION_PCT,
    MAX_STOP_LOSS_PCT,
    MIN_TRADE_SIZE_USD,
    validate_order,
)


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
        assert snap["allowed_pairs"] == ALLOWED_PAIRS


class TestGuardrailsFail:
    def test_disallowed_pair(self):
        result = validate_order(**_valid_order(pair_symbol="DOGE/USDT"))
        assert not result.passed
        assert any("not in allowed" in v for v in result.violations)

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
