# Changelog: feature/trading-toolkit

**Branch**: `feature/trading-toolkit`
**Created**: 2026-04-03
**ES Plan**: ES-0012 — inotagent-trading

## Summary

Trading toolkit for Robin — CLI tools, data pollers, backtesting engine, 6 strategies, and portfolio management. Lives in `inotagent-trading/` subfolder.

## Changes

### Phase 1: Foundation
- [x] Create `inotagent-trading/` subfolder + `pyproject.toml` + `Dockerfile` + `.dockerignore`
- [x] Write `core/config.py` (pydantic-settings), `core/db.py` (async + sync), `core/models.py` (enums + dataclasses)
- [x] Write DB migrations (008-012): core, accounts, orders, portfolio, backtest — 26 tables, 5 views, 13 indexes
- [x] Write `guardrails.py` (runtime trade validation) + `tests/test_guardrails.py` (18 tests)
- [x] Add `.env.template`, `Makefile` (auto-loads .env)

### Phase 2: Core Libraries
- [x] `core/exchange.py` — CcxtExchange (live) + PaperExchange (simulated fills at bid/ask)
- [x] `core/exchange.py` — Sub-account support (Crypto.com UUID), exchange-agnostic fetch_balance
- [x] `core/indicators.py` — daily TA (RSI, EMA, SMA, MACD, ATR, BB, Keltner, ADX, regime score) + intraday TA
- [x] `core/filters.py` — BTC correlation filter + portfolio drawdown guard
- [x] Tests: 12 exchange + 21 indicators

### Phase 3: Pollers
- [x] `poller/base.py` — retry with exponential backoff, health heartbeat JSON, cycle timing
- [x] `poller/public/` — loads pairs from DB (not env), defensive `_to_decimal()`, exchange-agnostic
- [x] `poller/private/` — iterates all venue accounts, syncs balances, detects fills, anomaly checks
- [x] `poller/ta/` — intraday + daily TA computation, paper stop-loss monitoring, ohlcv_1m pruning
- [x] Docker Compose services (poller-public, poller-private, poller-ta) with `trading` profile
- [x] Root Makefile targets: `trading-start/stop/status/logs/migrate/test`
- [x] Tests: 8 poller tests (retry, health, run loop)
- [x] Verified: public poller runs continuously, 1m candles accumulate in DB

### Phase 4: CLI Tools (38 commands total)
- [x] `cli/market.py` — 16 commands: setup (add-asset/venue/mapping/network/account/pair), data (overview/price/ta/history), seed-daily, fetch-daily (CoinGecko API), compute-daily-ta, backfill-daily-ta, coverage, poller-status
- [x] `cli/strategy.py` — 8 commands: list, create, view, history, update (SCD Type 2), activate, deactivate, set-mode
- [x] `cli/trade.py` — buy (guardrails + paper/live), sell (FIFO cost basis + P&L), cancel (DB + exchange), list-orders. `--live` flag for exchange orders.
- [x] `cli/signals.py` — scan (strategy registry + intraday execution guards), check (daily + intraday + guard status)
- [x] `cli/portfolio.py` — balance, accounts, pnl, transfers, transfer, snapshot, benchmark, history, reconcile-orders, reconcile-pnl
- [x] `cli/backtest.py` — run, sweep (param grid), list, view + DB persistence

### Phase 5: Strategies + Backtest
- [x] `strategies/base.py` — abstract interface (evaluate_signal + should_exit)
- [x] `strategies/momentum.py` — RSI/EMA/ADX/volume/regime weighted confidence (+15.0%, 42% WR)
- [x] `strategies/trend_follow.py` — ATR trailing stop, golden cross, breakout (+17.2%, 50% WR)
- [x] `strategies/volatility_breakout.py` — BB/Keltner squeeze detection (+0.0%, 100% WR)
- [x] `strategies/mean_reversion.py` — BB lower band + RSI oversold in sideways (-0.3%, 40% WR)
- [x] `strategies/rsi_divergence.py` — bullish RSI divergence reversal (+0.6%, 39% WR)
- [x] `strategies/bollinger.py` — BB mean reversion baseline
- [x] Improved regime score: 3-component (ADX × 0.4 + EMA slope × 0.4 + volatility ratio × 0.2)
- [x] Keltner Channels, squeeze detection, EMA(8), high_20d in indicators
- [x] Custom indicators stored in JSONB column (no migration needed)
- [x] Seeded 2667 days CRO historical OHLCV from CoinMarketCap CSV
- [x] Backfilled daily TA indicators for full history
- [x] Param sweep: 27 momentum + 32 bollinger + 18 scout + 27 divergence + 27 mean reversion combos tested
- [x] Backtested all strategies over 2 years (2024-2026): all beat HODL (-29.8%)

### Phase 5: Trading Skills + Recurring Tasks
- [x] `1__trading_signal_workflow.md` — hourly scan flow, decision logic, execution steps
- [x] `1__trading_portfolio_management.md` — daily/weekly review, P&L monitoring, escalation rules
- [x] `1__trading_strategy_reference.md` — regime coverage, strategy params, guardrails, filters
- [x] Removed old generic `1__trading_analysis.md` + `1__trading_operations.md`
- [x] 5 recurring tasks: ROB-010 (hourly scan), ROB-011 (daily P&L), ROB-012 (daily data refresh), ROB-013 (weekly review), ROB-014 (weekly backtest)

### Live Exchange Verification
- [x] Crypto.com Exchange API: balance sync (1307.6 CRO from sub-account)
- [x] Live order placement + cancellation on exchange + DB
- [x] CoinGecko API: daily OHLCV fetch for ongoing data

### Signal Architecture
- [x] Dual data source: CoinGecko (market-wide, daily signals) + Exchange (venue-specific, intraday guards)
- [x] Intraday execution guards: venue RSI > 75, spread > 0.5%, volatility spike > 2× ATR
- [x] Portfolio filters: BTC correlation (blocks when BTC crashing), drawdown > 15%

### Migration + Infra
- [x] Consolidated all migrations into shared `infra/postgres/migrations/` (dbmate, 001-012)
- [x] Hardcoded schema names: `openvaia` (platform) + `trading_platform` (trading)
- [x] Updated default schema from `platform` → `openvaia` across all code
- [x] Docker Compose services for 3 pollers with `trading` profile

### ES-0012 Spec Updates
- [x] Renamed `_usdt` → `_usd` (currency-agnostic)
- [x] Removed CODEOWNERS (Robin is CLI-only)
- [x] Reordered migrations: accounts before orders for FK dependency
- [x] Added data source architecture, strategy portfolio, intraday guards documentation
- [x] Monorepo structure, deployment model, env separation

### Remaining (post-merge)
- [ ] Phase 6: Activate strategies for paper trading, let Robin run 1-2 weeks
- [ ] Phase 6: Human review results → switch approved strategies to live
- [ ] Bake toolkit into agent Docker image (for Docker deployment)
- [ ] Update CLAUDE.md, project_summary.md with trading toolkit counts
