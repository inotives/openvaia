# Changelog: feature/trading-toolkit

**Branch**: `feature/trading-toolkit`
**Created**: 2026-04-03
**ES Plan**: ES-0012 — inotagent-trading

## Summary

Trading toolkit for Robin — CLI tools, data pollers, and backtesting engine. Lives in `inotagent-trading/` subfolder.

## Changes

### Phase 1: Foundation
- [x] Create `inotagent-trading/` subfolder + `pyproject.toml` + `Dockerfile` + `.dockerignore`
- [x] Write `core/config.py` (pydantic-settings), `core/db.py` (async + sync), `core/models.py` (enums + dataclasses)
- [x] Write DB migrations (001-005): core, accounts, orders, portfolio, backtest — 26 tables, 5 views, 13 indexes
- [x] Write `guardrails.py` (runtime trade validation) + `tests/test_guardrails.py` (18 tests)
- [x] Add `.env.template` with DATABASE_URL for dbmate
- [x] Add `Makefile` with migrate, test, lint targets (auto-loads .env)
- [x] Migrations verified against local Postgres — all 5 applied successfully

### Phase 2: Core Libraries
- [x] Write `core/exchange.py` — CcxtExchange (live) + PaperExchange (simulated fills at bid/ask)
- [x] Write `core/indicators.py` — daily TA (RSI, EMA, SMA, MACD, ATR, BB, ADX, regime score) + intraday TA (RSI, EMA, VWAP, spread, volatility)
- [x] Write `tests/test_exchange.py` (12 tests) — paper fill simulation, fee calculation, passthrough
- [x] Write `tests/test_indicators.py` (21 tests) — all indicator columns, edge cases

### ES-0012 spec updates (same branch)
- [x] Renamed `_usdt` → `_usd` across all column names (currency-agnostic)
- [x] Removed CODEOWNERS references (not needed — Robin is CLI-only)
- [x] Reordered migrations: accounts (002) before orders (003) for FK dependency
- [x] Updated migration section headers to match new order
