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

### Phase 3: Pollers
- [x] Write `poller/base.py` — retry with exponential backoff (1s/4s/16s), health heartbeat to JSON file, cycle timing
- [x] Write `poller/public/` — fetches 1m OHLCV + ticker (bid/ask/spread) for all active pairs
- [x] Write `poller/private/` — syncs balances, detects order fills, anomaly checks (consecutive losses, daily loss)
- [x] Write `poller/ta/` — intraday TA from 1m candles, daily TA (once/day), paper stop-loss monitoring, ohlcv_1m pruning
- [x] Add Docker Compose services (poller-public, poller-private, poller-ta) with `trading` profile
- [x] Add root Makefile targets: `trading-start`, `trading-stop`, `trading-status`, `trading-logs`, `trading-migrate`, `trading-test`
- [x] Write `tests/test_poller.py` (8 tests) — retry logic, health heartbeat, run loop

### Phase 4: CLI Tools
- [x] Write `cli/__init__.py` — shared JSON encoder + output/error helpers
- [x] Write `cli/market.py` — 14 commands: add-asset, add-venue, add-mapping, add-network, add-network-mapping, add-trading-pair, add-account, overview, price, ta, history, seed-daily, coverage, poller-status
- [x] Write `cli/strategy.py` — 8 commands: list, create, view, history, update (SCD Type 2), activate, deactivate, set-mode
- [x] Write `cli/trade.py` — 4 commands: buy (with guardrail validation + paper instant fill + cost basis), sell (with FIFO lot consumption + realized P&L), cancel, list-orders
- [x] Write `cli/signals.py` — 2 commands: scan (momentum evaluation + confidence scoring), check
- [x] Write `cli/portfolio.py` — 10 commands: balance, accounts, pnl, transfers, transfer, snapshot, benchmark, history, reconcile-orders, reconcile-pnl
- [x] All CLI modules verified against local Postgres

### Migration consolidation
- [x] Moved all migrations to shared `infra/postgres/migrations/` (dbmate, 001-012)
- [x] Hardcoded schema names: `openvaia` (platform) + `trading_platform` (trading)
- [x] Fixed `${SCHEMA}` variable substitution in 006-007
- [x] Fixed COALESCE in UNIQUE constraints → CREATE UNIQUE INDEX
- [x] Simplified `local-migrate` Makefile target

### ES-0012 spec updates (same branch)
- [x] Renamed `_usdt` → `_usd` across all column names (currency-agnostic)
- [x] Removed CODEOWNERS references (not needed — Robin is CLI-only)
- [x] Reordered migrations: accounts (002) before orders (003) for FK dependency
- [x] Updated migration section headers to match new order
