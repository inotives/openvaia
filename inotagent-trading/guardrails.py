"""Trading guardrails — runtime safety limits for all trade operations.

Two layers:
1. HARD CEILINGS (this file) — code-enforced, can never be exceeded, requires redeploy
2. OPERATIONAL LIMITS (DB) — tunable via CLI/UI within the ceilings

Effective limit = min(db_limit, hard_ceiling) for maxes
                  max(db_limit, hard_floor) for mins
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

# ── Hard Ceilings (code-enforced, HUMAN-AUTHORED) ────────────────────────────
# These are the absolute limits. Even if DB config is changed to extreme values,
# these ceilings cannot be breached. Change requires code commit + redeploy.

HARD_MAX_POSITION_PCT = Decimal("0.25")      # Never more than 25% per trade
HARD_MAX_OPEN_POSITIONS = 10                  # Never more than 10 concurrent
HARD_MAX_STOP_LOSS_PCT = Decimal("0.15")     # Stop-loss never wider than 15%
HARD_MIN_TRADE_SIZE_USD = Decimal("1.0")     # Never trade less than $1
HARD_MAX_APPROVAL_PCT = Decimal("0.50")      # Approval threshold never above 50%
STOP_LOSS_REQUIRED = True                     # Always required, not configurable
PAPER_MODE_DEFAULT = True                     # Always default to paper

# ── Default Operational Limits (used when DB has no config) ──────────────────

DEFAULTS = {
    "max_position_pct": Decimal("0.10"),
    "max_daily_loss_pct": Decimal("0.05"),
    "max_open_positions": 3,
    "max_stop_loss_pct": Decimal("0.08"),
    "min_trade_size_usd": Decimal("5.0"),
    "human_approval_threshold": Decimal("0.20"),
}


# ── Load from DB ─────────────────────────────────────────────────────────────

def load_guardrail_config(conn=None, schema: str = "trading_platform") -> dict:
    """Load operational limits from DB config table. Falls back to DEFAULTS.

    Stores in openvaia.configs table with key prefix 'guardrail:'.
    """
    config = dict(DEFAULTS)

    if conn is None:
        return config

    try:
        cur = conn.execute(
            f"SELECT key, value FROM {schema}.configs WHERE key LIKE 'guardrail:%%'"
        )
        rows = cur.fetchall()
    except Exception:
        # Config table might not exist (e.g., trading_platform schema has no configs table)
        # Try openvaia.configs
        try:
            cur = conn.execute(
                "SELECT key, value FROM openvaia.configs WHERE key LIKE 'guardrail:%%'"
            )
            rows = cur.fetchall()
        except Exception:
            return config

    for row in rows:
        key = row["key"].replace("guardrail:", "")
        value = row["value"]
        if key in ("max_position_pct", "max_daily_loss_pct", "max_stop_loss_pct",
                    "min_trade_size_usd", "human_approval_threshold"):
            config[key] = Decimal(str(value))
        elif key == "max_open_positions":
            config[key] = int(value)

    return config


def _enforce_ceilings(config: dict) -> dict:
    """Clamp DB values to hard ceilings. DB can relax within bounds but not exceed."""
    c = dict(config)
    c["max_position_pct"] = min(c["max_position_pct"], HARD_MAX_POSITION_PCT)
    c["max_open_positions"] = min(c["max_open_positions"], HARD_MAX_OPEN_POSITIONS)
    c["max_stop_loss_pct"] = min(c["max_stop_loss_pct"], HARD_MAX_STOP_LOSS_PCT)
    c["min_trade_size_usd"] = max(c["min_trade_size_usd"], HARD_MIN_TRADE_SIZE_USD)
    c["human_approval_threshold"] = min(c["human_approval_threshold"], HARD_MAX_APPROVAL_PCT)
    return c


# ── Validation ───────────────────────────────────────────────────────────────

@dataclass
class GuardrailCheck:
    passed: bool
    violations: list[str]
    needs_human_approval: bool = False

    @property
    def snapshot(self) -> dict:
        """Capture guardrail values at time of check — stored on order for audit."""
        return {k: float(v) if isinstance(v, Decimal) else v for k, v in self._config.items()}


def validate_order(
    pair_symbol: str,
    side: str,
    amount_usd: Decimal,
    portfolio_value_usd: Decimal,
    open_position_count: int,
    daily_pnl_pct: Decimal,
    stop_loss_pct: Decimal | None = None,
    allowed_pairs: list[str] | None = None,
    config: dict | None = None,
) -> GuardrailCheck:
    """Validate a trade against guardrails.

    config: operational limits from load_guardrail_config(). If None, uses DEFAULTS.
    allowed_pairs: from trading_pairs table. If None, pair check skipped.
    """
    cfg = _enforce_ceilings(config or DEFAULTS)
    violations: list[str] = []
    needs_approval = False

    # Allowed pairs (from DB trading_pairs, not hardcoded)
    if allowed_pairs is not None and pair_symbol not in allowed_pairs:
        violations.append(f"Pair '{pair_symbol}' not in active trading pairs: {allowed_pairs}")

    # Min trade size
    min_size = cfg["min_trade_size_usd"]
    if amount_usd < min_size:
        violations.append(f"Trade size ${amount_usd} below minimum ${min_size}")

    # Position size limit
    max_pos = cfg["max_position_pct"]
    if portfolio_value_usd > 0:
        position_pct = amount_usd / portfolio_value_usd
        if position_pct > max_pos:
            violations.append(
                f"Position {position_pct:.1%} exceeds max {max_pos:.0%} of portfolio"
            )

        # Human approval threshold
        approval_pct = cfg["human_approval_threshold"]
        if position_pct > approval_pct:
            needs_approval = True

    # Max open positions (only for buys)
    max_open = cfg["max_open_positions"]
    if side == "buy" and open_position_count >= max_open:
        violations.append(f"Already {open_position_count} open positions (max {max_open})")

    # Daily loss limit
    max_loss = cfg["max_daily_loss_pct"]
    if daily_pnl_pct < -max_loss:
        violations.append(f"Daily loss {daily_pnl_pct:.1%} exceeds limit {-max_loss:.0%}")

    # Stop-loss required for buys (hard-coded, not configurable)
    if side == "buy" and STOP_LOSS_REQUIRED:
        if stop_loss_pct is None:
            violations.append("Stop-loss is required for all buy orders")
        else:
            max_sl = cfg["max_stop_loss_pct"]
            if stop_loss_pct > max_sl:
                violations.append(
                    f"Stop-loss {stop_loss_pct:.1%} wider than max {max_sl:.0%}"
                )

    result = GuardrailCheck(
        passed=len(violations) == 0,
        violations=violations,
        needs_human_approval=needs_approval,
    )
    result._config = cfg  # Attach for snapshot
    return result
