"""Trading guardrails — runtime safety limits for all trade operations.

HUMAN-AUTHORED. All trade commands validate against these before execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

# ── Guardrail Constants ──────────────────────────────────────────────────────

MAX_POSITION_PCT = Decimal("0.10")          # Max 10% of portfolio per trade
MAX_DAILY_LOSS_PCT = Decimal("0.05")        # Stop trading if daily loss > 5%
MAX_OPEN_POSITIONS = 3                      # Max 3 concurrent positions
STOP_LOSS_REQUIRED = True                   # Every buy must have stop-loss
MAX_STOP_LOSS_PCT = Decimal("0.08")         # Stop-loss can't be wider than 8%
MIN_TRADE_SIZE_USD = Decimal("5.0")        # Minimum trade size
HUMAN_APPROVAL_THRESHOLD = Decimal("0.20")  # Trades > 20% of portfolio need human approval
ALLOWED_PAIRS = ["CRO/USDT"]                # Only approved trading pairs
PAPER_MODE_DEFAULT = True                   # New strategies start in paper mode


# ── Validation ───────────────────────────────────────────────────────────────


@dataclass
class GuardrailCheck:
    passed: bool
    violations: list[str]
    needs_human_approval: bool = False

    @property
    def snapshot(self) -> dict:
        """Capture guardrail values at time of check — stored on order for audit."""
        return {
            "max_position_pct": float(MAX_POSITION_PCT),
            "max_daily_loss_pct": float(MAX_DAILY_LOSS_PCT),
            "max_open_positions": MAX_OPEN_POSITIONS,
            "stop_loss_required": STOP_LOSS_REQUIRED,
            "max_stop_loss_pct": float(MAX_STOP_LOSS_PCT),
            "min_trade_size_usd": float(MIN_TRADE_SIZE_USD),
            "human_approval_threshold": float(HUMAN_APPROVAL_THRESHOLD),
            "allowed_pairs": ALLOWED_PAIRS,
        }


def validate_order(
    pair_symbol: str,
    side: str,
    amount_usd: Decimal,
    portfolio_value_usd: Decimal,
    open_position_count: int,
    daily_pnl_pct: Decimal,
    stop_loss_pct: Decimal | None = None,
) -> GuardrailCheck:
    """Validate a trade against all guardrails. Returns pass/fail + violations."""
    violations: list[str] = []
    needs_approval = False

    # Allowed pairs
    if pair_symbol not in ALLOWED_PAIRS:
        violations.append(f"Pair '{pair_symbol}' not in allowed list: {ALLOWED_PAIRS}")

    # Min trade size
    if amount_usd < MIN_TRADE_SIZE_USD:
        violations.append(f"Trade size ${amount_usd} below minimum ${MIN_TRADE_SIZE_USD}")

    # Position size limit
    if portfolio_value_usd > 0:
        position_pct = amount_usd / portfolio_value_usd
        if position_pct > MAX_POSITION_PCT:
            violations.append(
                f"Position {position_pct:.1%} exceeds max {MAX_POSITION_PCT:.0%} of portfolio"
            )

        # Human approval threshold
        if position_pct > HUMAN_APPROVAL_THRESHOLD:
            needs_approval = True

    # Max open positions (only for buys)
    if side == "buy" and open_position_count >= MAX_OPEN_POSITIONS:
        violations.append(f"Already {open_position_count} open positions (max {MAX_OPEN_POSITIONS})")

    # Daily loss limit
    if daily_pnl_pct < -MAX_DAILY_LOSS_PCT:
        violations.append(f"Daily loss {daily_pnl_pct:.1%} exceeds limit {-MAX_DAILY_LOSS_PCT:.0%}")

    # Stop-loss required for buys
    if side == "buy" and STOP_LOSS_REQUIRED:
        if stop_loss_pct is None:
            violations.append("Stop-loss is required for all buy orders")
        elif stop_loss_pct > MAX_STOP_LOSS_PCT:
            violations.append(
                f"Stop-loss {stop_loss_pct:.1%} wider than max {MAX_STOP_LOSS_PCT:.0%}"
            )

    return GuardrailCheck(
        passed=len(violations) == 0,
        violations=violations,
        needs_human_approval=needs_approval,
    )
