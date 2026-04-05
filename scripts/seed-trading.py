#!/usr/bin/env python3
"""Seed trading reference data + strategies for inotagent-trading.

Sets up: assets, venues, mappings, trading pairs, account, and strategies.
Safe to re-run — skips existing records.

Usage:
    python3 scripts/seed-trading.py
    python3 scripts/seed-trading.py --force   # delete and re-create strategies
"""

import json
import os
import sys
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row

# ── Reference Data ───────────────────────────────────────────────────────────

ASSETS = [
    {"symbol": "BTC", "name": "Bitcoin"},
    {"symbol": "ETH", "name": "Ethereum"},
    {"symbol": "SOL", "name": "Solana"},
    {"symbol": "XRP", "name": "Ripple"},
    {"symbol": "USD", "name": "US Dollar"},
    {"symbol": "USDT", "name": "Tether"},
]

VENUES = [
    {"code": "cryptocom", "name": "Crypto.com", "type": "exchange", "ccxt_id": "cryptocom"},
    {"code": "coingecko", "name": "CoinGecko", "type": "data", "ccxt_id": None},
    {"code": "coinmarketcap", "name": "CoinMarketCap", "type": "data", "ccxt_id": None},
]

# CoinGecko asset mappings (for daily OHLCV fetch)
COINGECKO_MAPPINGS = [
    {"asset": "BTC", "external_id": "bitcoin"},
    {"asset": "ETH", "external_id": "ethereum"},
    {"asset": "SOL", "external_id": "solana"},
    {"asset": "XRP", "external_id": "ripple"},
]

# Trading pairs on Crypto.com Exchange
TRADING_PAIRS = [
    # Spot pairs
    {"base": "BTC", "quote": "USD", "pair_symbol": "BTC/USD", "maker_fee": "0.0025", "taker_fee": "0.005"},
    {"base": "ETH", "quote": "USD", "pair_symbol": "ETH/USD", "maker_fee": "0.0025", "taker_fee": "0.005"},
    {"base": "SOL", "quote": "USD", "pair_symbol": "SOL/USD", "maker_fee": "0.0025", "taker_fee": "0.005"},
    {"base": "XRP", "quote": "USD", "pair_symbol": "XRP/USD", "maker_fee": "0.0025", "taker_fee": "0.005"},
    # Perpetual pairs (for funding rate + futures trading)
    {"base": "BTC", "quote": "USD", "pair_symbol": "BTC/USD:USD", "maker_fee": "0.00015", "taker_fee": "0.00045"},
    {"base": "ETH", "quote": "USD", "pair_symbol": "ETH/USD:USD", "maker_fee": "0.00015", "taker_fee": "0.00045"},
    {"base": "SOL", "quote": "USD", "pair_symbol": "SOL/USD:USD", "maker_fee": "0.00015", "taker_fee": "0.00045"},
    {"base": "XRP", "quote": "USD", "pair_symbol": "XRP/USD:USD", "maker_fee": "0.00015", "taker_fee": "0.00045"},
]

# Default account on Crypto.com Exchange
ACCOUNTS = [
    {"venue": "cryptocom", "name": "robin vault", "account_type": "spot", "is_default": True},
]

# ── Strategies (v3, tuned on 6-month data) ───────────────────────────────────

STRATEGIES = [
    # Momentum — buy RSI oversold dips in moderate regimes
    {
        "name": "btc_momentum", "type": "momentum", "asset": "BTC",
        "params": {
            "entry": {"rsi_buy_threshold": 30, "min_adx": 15, "volume_ratio_min": 1.5, "min_regime_score": 50},
            "exit": {"take_profit_pct": 8, "stop_loss_pct": 3},
            "position": {"capital_per_trade_pct": 10},
        },
    },
    {
        "name": "eth_momentum", "type": "momentum", "asset": "ETH",
        "params": {
            "entry": {"rsi_buy_threshold": 30, "min_adx": 15, "volume_ratio_min": 1.5, "min_regime_score": 50},
            "exit": {"take_profit_pct": 8, "stop_loss_pct": 8},
            "position": {"capital_per_trade_pct": 10},
        },
    },
    {
        "name": "sol_momentum", "type": "momentum", "asset": "SOL",
        "params": {
            "entry": {"rsi_buy_threshold": 30, "min_adx": 15, "volume_ratio_min": 1.5, "min_regime_score": 50},
            "exit": {"take_profit_pct": 8, "stop_loss_pct": 8},
            "position": {"capital_per_trade_pct": 10},
        },
    },
    {
        "name": "xrp_momentum", "type": "momentum", "asset": "XRP",
        "params": {
            "entry": {"rsi_buy_threshold": 40, "min_adx": 15, "volume_ratio_min": 1.5, "min_regime_score": 40},
            "exit": {"take_profit_pct": 8, "stop_loss_pct": 8},
            "position": {"capital_per_trade_pct": 10},
        },
    },
    # Trend follow — ride strong uptrends with ATR trailing stop (tuned on bull period Jun 2024 - Nov 2025)
    {
        "name": "btc_trend_follow", "type": "trend_follow", "asset": "BTC",
        "params": {
            "entry": {"min_regime_score": 40, "min_adx": 15, "rsi_entry_max": 70, "max_atr_pct": 6.0},
            "exit": {"atr_stop_multiplier": 2.0, "atr_trail_multiplier": 4.0, "take_profit_pct": 20},
            "position": {"capital_per_trade_pct": 15, "risk_pct_per_trade": 1.0},
        },
    },
    {
        "name": "eth_trend_follow", "type": "trend_follow", "asset": "ETH",
        "params": {
            "entry": {"min_regime_score": 61, "min_adx": 25, "rsi_entry_max": 70, "max_atr_pct": 6.0},
            "exit": {"atr_stop_multiplier": 2.0, "atr_trail_multiplier": 2.0, "take_profit_pct": 20},
            "position": {"capital_per_trade_pct": 15, "risk_pct_per_trade": 1.0},
        },
    },
    {
        "name": "sol_trend_follow", "type": "trend_follow", "asset": "SOL",
        "params": {
            "entry": {"min_regime_score": 50, "min_adx": 15, "rsi_entry_max": 70, "max_atr_pct": 6.0},
            "exit": {"atr_stop_multiplier": 2.0, "atr_trail_multiplier": 2.0, "take_profit_pct": 20},
            "position": {"capital_per_trade_pct": 15, "risk_pct_per_trade": 1.0},
        },
    },
    {
        "name": "xrp_trend_follow", "type": "trend_follow", "asset": "XRP",
        "params": {
            "entry": {"min_regime_score": 50, "min_adx": 15, "rsi_entry_max": 70, "max_atr_pct": 6.0},
            "exit": {"atr_stop_multiplier": 2.0, "atr_trail_multiplier": 3.0, "take_profit_pct": 20},
            "position": {"capital_per_trade_pct": 15, "risk_pct_per_trade": 1.0},
        },
    },
    # Pyramid Trend — scale into winners with asymmetric LIFO exits (tuned)
    {
        "name": "btc_pyramid_trend", "type": "pyramid_trend", "asset": "BTC",
        "params": {
            "entry": {"min_regime_score": 40, "min_adx": 15, "rsi_entry_max": 75, "min_conditions": 4},
            "pyramid": {
                "allocations": {"A": 40, "B": 30, "C": 20, "D": 10},
                "thresholds": {"B": 5.0, "C": 12.0, "D": 20.0},
                "cooldown_days": 5,
            },
            "exit": {
                "lot_d_trail_pct": 5.0, "lot_d_rsi_exit": 80,
                "lot_c_trail_pct": 10.0,
                "lot_b_trail_pct": 12.0,
                "lot_a_exit_regime": 45, "lot_a_trail_pct": 25.0,
                "hard_stop_pct": 5.0,
            },
            "position": {"capital_per_trade_pct": 20},
        },
    },
    {
        "name": "eth_pyramid_trend", "type": "pyramid_trend", "asset": "ETH",
        "params": {
            "entry": {"min_regime_score": 40, "min_adx": 15, "rsi_entry_max": 75, "min_conditions": 4},
            "pyramid": {
                "allocations": {"A": 40, "B": 30, "C": 20, "D": 10},
                "thresholds": {"B": 3.0, "C": 12.0, "D": 20.0},
                "cooldown_days": 5,
            },
            "exit": {
                "lot_d_trail_pct": 5.0, "lot_d_rsi_exit": 80,
                "lot_c_trail_pct": 10.0,
                "lot_b_trail_pct": 15.0,
                "lot_a_exit_regime": 45, "lot_a_trail_pct": 25.0,
                "hard_stop_pct": 5.0,
            },
            "position": {"capital_per_trade_pct": 20},
        },
    },
    {
        "name": "sol_pyramid_trend", "type": "pyramid_trend", "asset": "SOL",
        "params": {
            "entry": {"min_regime_score": 45, "min_adx": 15, "rsi_entry_max": 75, "min_conditions": 4},
            "pyramid": {
                "allocations": {"A": 40, "B": 30, "C": 20, "D": 10},
                "thresholds": {"B": 5.0, "C": 12.0, "D": 20.0},
                "cooldown_days": 5,
            },
            "exit": {
                "lot_d_trail_pct": 3.0, "lot_d_rsi_exit": 80,
                "lot_c_trail_pct": 7.0,
                "lot_b_trail_pct": 15.0,
                "lot_a_exit_regime": 40, "lot_a_trail_pct": 25.0,
                "hard_stop_pct": 5.0,
            },
            "position": {"capital_per_trade_pct": 20},
        },
    },
    {
        "name": "xrp_pyramid_trend", "type": "pyramid_trend", "asset": "XRP",
        "params": {
            "entry": {"min_regime_score": 45, "min_adx": 15, "rsi_entry_max": 75, "min_conditions": 4},
            "pyramid": {
                "allocations": {"A": 40, "B": 30, "C": 20, "D": 10},
                "thresholds": {"B": 5.0, "C": 12.0, "D": 20.0},
                "cooldown_days": 5,
            },
            "exit": {
                "lot_d_trail_pct": 3.0, "lot_d_rsi_exit": 80,
                "lot_c_trail_pct": 7.0,
                "lot_b_trail_pct": 15.0,
                "lot_a_exit_regime": 40, "lot_a_trail_pct": 25.0,
                "hard_stop_pct": 5.0,
            },
            "position": {"capital_per_trade_pct": 20},
        },
    },
    # Volatility Breakout — catches sharp bursts from BB squeeze breakouts
    {
        "name": "btc_volatility_breakout", "type": "volatility_breakout", "asset": "BTC",
        "params": {
            "entry": {"max_bb_width_squeeze": 3.0, "adx_threshold": 20, "rvol_min": 1.5, "min_conditions": 3},
            "exit": {"stop_atr_mult": 1.5, "time_stop_days": 3},
            "position": {"capital_per_trade_pct": 5, "risk_pct_per_trade": 0.5},
        },
    },
    {
        "name": "eth_volatility_breakout", "type": "volatility_breakout", "asset": "ETH",
        "params": {
            "entry": {"max_bb_width_squeeze": 3.5, "adx_threshold": 20, "rvol_min": 1.5, "min_conditions": 3},
            "exit": {"stop_atr_mult": 1.5, "time_stop_days": 3},
            "position": {"capital_per_trade_pct": 5, "risk_pct_per_trade": 0.5},
        },
    },
    {
        "name": "sol_volatility_breakout", "type": "volatility_breakout", "asset": "SOL",
        "params": {
            "entry": {"max_bb_width_squeeze": 4.0, "adx_threshold": 20, "rvol_min": 1.5, "min_conditions": 3},
            "exit": {"stop_atr_mult": 1.5, "time_stop_days": 3},
            "position": {"capital_per_trade_pct": 5, "risk_pct_per_trade": 0.5},
        },
    },
    {
        "name": "xrp_volatility_breakout", "type": "volatility_breakout", "asset": "XRP",
        "params": {
            "entry": {"max_bb_width_squeeze": 4.0, "adx_threshold": 20, "rvol_min": 1.5, "min_conditions": 3},
            "exit": {"stop_atr_mult": 1.5, "time_stop_days": 3},
            "position": {"capital_per_trade_pct": 5, "risk_pct_per_trade": 0.5},
        },
    },
    # DCA Grid — maker-only execution, regime-based mode switching (tuned on 6mo bear data)
    {
        "name": "btc_dca_grid", "type": "dca_grid", "asset": "BTC",
        "params": {
            "mode": {
                "default": "adaptive_fifo",
                "auto_select_by_regime": True,
                "batch_regime_max": 30,
                "fifo_regime_min": 30,
                "regime_pause_threshold": 65,
                "regime_resume_threshold": 55,
            },
            "entry": {
                "max_regime_score": 65,
                "rsi_entry_max": 60,
                "max_atr_pct": 6.0,
                "defensive_mode_enabled": True,
                "defensive_rsi_oversold": 25,
            },
            "grid": {
                "num_levels": 5,
                "weights": [1, 1, 2, 3, 3],
                "volatility_regimes": {
                    "low": {"atr_mult": 0.15, "profit_target": 1.0},
                    "normal": {"atr_mult": 0.15, "profit_target": 1.5},
                    "high": {"atr_mult": 0.3, "profit_target": 2.0},
                },
            },
            "exit": {
                "stop_loss_spacing_mult": 1.0,
                "stop_loss_type": "exchange_trigger",
                "max_cycle_duration_hours": 72,
                "max_expired_pending_per_asset": 2,
                "cooldown_minutes": 30,
            },
            "position": {"capital_per_cycle_pct": 10},
        },
    },
    {
        "name": "eth_dca_grid", "type": "dca_grid", "asset": "ETH",
        "params": {
            "mode": {
                "default": "adaptive_fifo",
                "auto_select_by_regime": True,
                "batch_regime_max": 30,
                "fifo_regime_min": 30,
                "regime_pause_threshold": 65,
                "regime_resume_threshold": 55,
            },
            "entry": {
                "max_regime_score": 65,
                "rsi_entry_max": 60,
                "max_atr_pct": 8.0,
                "defensive_mode_enabled": True,
                "defensive_rsi_oversold": 25,
            },
            "grid": {
                "num_levels": 5,
                "weights": [1, 1, 2, 3, 3],
                "volatility_regimes": {
                    "low": {"atr_mult": 0.15, "profit_target": 1.5},
                    "normal": {"atr_mult": 0.2, "profit_target": 2.0},
                    "high": {"atr_mult": 0.4, "profit_target": 2.5},
                },
            },
            "exit": {
                "stop_loss_spacing_mult": 1.0,
                "stop_loss_type": "exchange_trigger",
                "max_cycle_duration_hours": 72,
                "max_expired_pending_per_asset": 2,
                "cooldown_minutes": 30,
            },
            "position": {"capital_per_cycle_pct": 10},
        },
    },
    {
        "name": "sol_dca_grid", "type": "dca_grid", "asset": "SOL",
        "params": {
            "mode": {
                "default": "adaptive_fifo",
                "auto_select_by_regime": True,
                "batch_regime_max": 30,
                "fifo_regime_min": 30,
                "regime_pause_threshold": 65,
                "regime_resume_threshold": 55,
            },
            "entry": {
                "max_regime_score": 65,
                "rsi_entry_max": 60,
                "max_atr_pct": 10.0,
                "defensive_mode_enabled": True,
                "defensive_rsi_oversold": 25,
            },
            "grid": {
                "num_levels": 5,
                "weights": [1, 1, 2, 3, 3],
                "volatility_regimes": {
                    "low": {"atr_mult": 0.2, "profit_target": 2.0},
                    "normal": {"atr_mult": 0.3, "profit_target": 2.5},
                    "high": {"atr_mult": 0.5, "profit_target": 3.0},
                },
            },
            "exit": {
                "stop_loss_spacing_mult": 1.0,
                "stop_loss_type": "exchange_trigger",
                "max_cycle_duration_hours": 72,
                "max_expired_pending_per_asset": 2,
                "cooldown_minutes": 30,
            },
            "position": {"capital_per_cycle_pct": 8},
        },
    },
    {
        "name": "xrp_dca_grid", "type": "dca_grid", "asset": "XRP",
        "params": {
            "mode": {
                "default": "adaptive_fifo",
                "auto_select_by_regime": True,
                "batch_regime_max": 30,
                "fifo_regime_min": 30,
                "regime_pause_threshold": 65,
                "regime_resume_threshold": 55,
            },
            "entry": {
                "max_regime_score": 65,
                "rsi_entry_max": 60,
                "max_atr_pct": 10.0,
                "defensive_mode_enabled": True,
                "defensive_rsi_oversold": 25,
            },
            "grid": {
                "num_levels": 5,
                "weights": [1, 1, 2, 3, 3],
                "volatility_regimes": {
                    "low": {"atr_mult": 0.2, "profit_target": 2.0},
                    "normal": {"atr_mult": 0.3, "profit_target": 3.0},
                    "high": {"atr_mult": 0.5, "profit_target": 3.5},
                },
            },
            "exit": {
                "stop_loss_spacing_mult": 1.0,
                "stop_loss_type": "exchange_trigger",
                "max_cycle_duration_hours": 72,
                "max_expired_pending_per_asset": 2,
                "cooldown_minutes": 30,
            },
            "position": {"capital_per_cycle_pct": 8},
        },
    },
]


def main():
    force = "--force" in sys.argv
    schema = os.environ.get("TRADING_SCHEMA", "trading_platform")

    with psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5445")),
        user=os.environ.get("POSTGRES_USER", "inotives"),
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ.get("POSTGRES_DB", "inotives"),
        row_factory=dict_row,
        autocommit=True,
    ) as conn:
        s = schema

        # ── Assets ──
        for asset in ASSETS:
            cur = conn.execute(f"SELECT 1 FROM {s}.assets WHERE symbol = %s", (asset["symbol"],))
            if cur.fetchone():
                print(f"  SKIP asset {asset['symbol']}")
            else:
                conn.execute(
                    f"INSERT INTO {s}.assets (symbol, name, created_by) VALUES (%s, %s, 'seed')",
                    (asset["symbol"], asset["name"]),
                )
                print(f"  OK   asset {asset['symbol']}")

        # ── Venues ──
        for venue in VENUES:
            cur = conn.execute(f"SELECT 1 FROM {s}.venues WHERE code = %s", (venue["code"],))
            if cur.fetchone():
                print(f"  SKIP venue {venue['code']}")
            else:
                conn.execute(
                    f"INSERT INTO {s}.venues (code, name, type, ccxt_id, created_by) VALUES (%s, %s, %s, %s, 'seed')",
                    (venue["code"], venue["name"], venue["type"], venue["ccxt_id"]),
                )
                print(f"  OK   venue {venue['code']}")

        # ── CoinGecko mappings ──
        cg_venue = conn.execute(f"SELECT id FROM {s}.venues WHERE code = 'coingecko'").fetchone()
        if cg_venue:
            for m in COINGECKO_MAPPINGS:
                asset_row = conn.execute(f"SELECT id FROM {s}.assets WHERE symbol = %s", (m["asset"],)).fetchone()
                if not asset_row:
                    continue
                cur = conn.execute(
                    f"SELECT 1 FROM {s}.asset_mappings WHERE asset_id = %s AND venue_id = %s",
                    (asset_row["id"], cg_venue["id"]),
                )
                if cur.fetchone():
                    print(f"  SKIP mapping {m['asset']} → coingecko")
                else:
                    conn.execute(
                        f"INSERT INTO {s}.asset_mappings (asset_id, venue_id, external_id, created_by) VALUES (%s, %s, %s, 'seed')",
                        (asset_row["id"], cg_venue["id"], m["external_id"]),
                    )
                    print(f"  OK   mapping {m['asset']} → coingecko:{m['external_id']}")

        # ── Trading pairs ──
        cc_venue = conn.execute(f"SELECT id FROM {s}.venues WHERE code = 'cryptocom'").fetchone()
        if cc_venue:
            for tp in TRADING_PAIRS:
                base = conn.execute(f"SELECT id FROM {s}.assets WHERE symbol = %s", (tp["base"],)).fetchone()
                quote = conn.execute(f"SELECT id FROM {s}.assets WHERE symbol = %s", (tp["quote"],)).fetchone()
                if not base or not quote:
                    continue
                cur = conn.execute(
                    f"SELECT 1 FROM {s}.trading_pairs WHERE venue_id = %s AND pair_symbol = %s AND is_current = true",
                    (cc_venue["id"], tp["pair_symbol"]),
                )
                if cur.fetchone():
                    print(f"  SKIP pair {tp['pair_symbol']}")
                else:
                    conn.execute(
                        f"""INSERT INTO {s}.trading_pairs
                            (venue_id, base_asset_id, quote_asset_id, pair_symbol, maker_fee, taker_fee, created_by)
                            VALUES (%s, %s, %s, %s, %s, %s, 'seed')""",
                        (cc_venue["id"], base["id"], quote["id"], tp["pair_symbol"], tp["maker_fee"], tp["taker_fee"]),
                    )
                    print(f"  OK   pair {tp['pair_symbol']}")

        # ── Accounts ──
        for acc in ACCOUNTS:
            venue_row = conn.execute(f"SELECT id FROM {s}.venues WHERE code = %s", (acc["venue"],)).fetchone()
            if not venue_row:
                continue
            cur = conn.execute(
                f"SELECT 1 FROM {s}.accounts WHERE venue_id = %s AND name = %s",
                (venue_row["id"], acc["name"]),
            )
            if cur.fetchone():
                print(f"  SKIP account {acc['venue']}:{acc['name']}")
            else:
                conn.execute(
                    f"""INSERT INTO {s}.accounts (venue_id, name, account_type, is_default, created_by)
                        VALUES (%s, %s, %s, %s, 'seed')""",
                    (venue_row["id"], acc["name"], acc["account_type"], acc["is_default"]),
                )
                print(f"  OK   account {acc['venue']}:{acc['name']}")

        # ── Strategies ──
        if force:
            conn.execute(f"DELETE FROM {s}.strategies WHERE name LIKE 'btc_%%' OR name LIKE 'eth_%%' OR name LIKE 'sol_%%' OR name LIKE 'xrp_%%'")
            print("  Deleted existing strategies (--force)")

        for strat in STRATEGIES:
            cur = conn.execute(
                f"SELECT 1 FROM {s}.strategies WHERE name = %s AND is_current = true",
                (strat["name"],),
            )
            if cur.fetchone():
                print(f"  SKIP strategy {strat['name']}")
                continue

            asset_row = conn.execute(f"SELECT id FROM {s}.assets WHERE symbol = %s", (strat["asset"],)).fetchone()
            venue_row = conn.execute(f"SELECT id FROM {s}.venues WHERE code = 'cryptocom'").fetchone()

            conn.execute(
                f"""INSERT INTO {s}.strategies
                    (name, type, asset_id, venue_id, params, is_active, paper_mode, created_by)
                    VALUES (%s, %s, %s, %s, %s, false, true, 'seed')""",
                (strat["name"], strat["type"], asset_row["id"], venue_row["id"], json.dumps(strat["params"])),
            )
            print(f"  OK   strategy {strat['name']} ({strat['type']}, {strat['asset']})")

        # ── Summary ──
        count = conn.execute(f"SELECT COUNT(*) AS n FROM {s}.strategies WHERE is_current = true").fetchone()
        print(f"\nDone. {count['n']} strategies in DB.")


if __name__ == "__main__":
    main()
