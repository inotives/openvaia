"""Portfolio-level filters — guards that can block signals across all strategies.

Usage in signal scanner or trade CLI:
    from core.filters import check_btc_filter
    block = check_btc_filter(conn, schema)
    if block:
        print(f"Signal blocked: {block}")
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def check_btc_filter(conn, schema: str, config: dict | None = None) -> str | None:
    """BTC Correlation Filter — blocks all buy signals when BTC is crashing.

    CRO (and most alts) are 80%+ correlated with BTC. If BTC is in freefall,
    buying CRO is almost guaranteed to lose money regardless of CRO's own signals.

    Returns None if OK to trade, or a reason string if blocked.
    """
    cfg = config or {}
    btc_rsi_min = cfg.get("btc_rsi_min", 20)
    btc_regime_min = cfg.get("btc_regime_min", 5)
    enabled = cfg.get("enabled", True)

    if not enabled:
        return None

    s = schema

    # Check if BTC exists in our assets
    cur = conn.execute(f"SELECT id FROM {s}.assets WHERE symbol = 'BTC' AND deleted_at IS NULL")
    btc = cur.fetchone()
    if not btc:
        return None  # No BTC data — can't filter, allow trade

    # Get latest BTC indicators
    cur = conn.execute(
        f"""SELECT rsi_14, regime_score, date
            FROM {s}.indicators_daily
            WHERE asset_id = %s
            ORDER BY date DESC LIMIT 1""",
        (btc["id"],),
    )
    row = cur.fetchone()
    if not row:
        return None  # No BTC indicators — allow trade

    btc_rsi = float(row["rsi_14"]) if row["rsi_14"] else 50
    btc_regime = float(row["regime_score"]) if row["regime_score"] else 50

    reasons = []
    if btc_rsi < btc_rsi_min:
        reasons.append(f"BTC RSI {btc_rsi:.1f} < {btc_rsi_min}")
    if btc_regime < btc_regime_min:
        reasons.append(f"BTC regime {btc_regime:.0f} < {btc_regime_min}")

    if reasons:
        msg = f"BTC correlation filter: {'; '.join(reasons)} — all buys paused"
        logger.warning(msg)
        return msg

    return None


def check_portfolio_drawdown(conn, schema: str, config: dict | None = None) -> str | None:
    """Portfolio drawdown guard — blocks new buys if portfolio is down too much.

    Prevents adding to losing positions during extended drawdowns.
    """
    cfg = config or {}
    max_drawdown_pct = cfg.get("max_portfolio_drawdown_pct", 15.0)
    enabled = cfg.get("enabled", True)

    if not enabled:
        return None

    s = schema

    # Get latest portfolio snapshot
    cur = conn.execute(
        f"""SELECT total_value_usd FROM {s}.portfolio_snapshots
            ORDER BY date DESC LIMIT 1"""
    )
    latest = cur.fetchone()
    if not latest or not latest["total_value_usd"]:
        return None

    # Get peak
    cur = conn.execute(
        f"SELECT MAX(total_value_usd) AS peak FROM {s}.portfolio_snapshots"
    )
    peak = cur.fetchone()
    if not peak or not peak["peak"] or float(peak["peak"]) == 0:
        return None

    current = float(latest["total_value_usd"])
    peak_val = float(peak["peak"])
    drawdown_pct = (current - peak_val) / peak_val * 100

    if drawdown_pct < -max_drawdown_pct:
        msg = f"Portfolio drawdown {drawdown_pct:.1f}% exceeds -{max_drawdown_pct}% limit — buys paused"
        logger.warning(msg)
        return msg

    return None
