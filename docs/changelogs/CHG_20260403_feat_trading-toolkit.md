# Changelog: feature/trading-toolkit

**Branch**: `feature/trading-toolkit`
**Created**: 2026-04-03
**ES Plan**: ES-0012 — inotagent-trading

## Summary

Trading toolkit for Robin — CLI tools, data pollers, backtesting engine, 6 strategies, and portfolio management. Lives in `inotagent-trading/` subfolder. Deployed and paper trading in Docker.

## Changes

### Phase 1: Foundation
- [x] `inotagent-trading/` subfolder + `pyproject.toml` + `Dockerfile` + `.dockerignore`
- [x] `core/config.py` (pydantic-settings), `core/db.py` (async + sync), `core/models.py`
- [x] DB migrations (008-012): 26 tables, 5 views, 13 indexes in `trading_platform` schema
- [x] `guardrails.py` — hybrid: hard ceilings in code, operational limits from DB
- [x] `.env.template`, `Makefile` (auto-loads .env)

### Phase 2: Core Libraries
- [x] `core/exchange.py` — CcxtExchange (live) + PaperExchange (simulated fills at bid/ask)
- [x] Sub-account support (Crypto.com UUID), exchange-agnostic `fetch_balance(account_address)`
- [x] `core/indicators.py` — daily TA (RSI, EMA, SMA, MACD, ATR, BB, Keltner, ADX) + intraday TA
- [x] Improved regime score: 3-component (ADX × 0.4 + EMA slope × 0.4 + volatility ratio × 0.2)
- [x] `core/filters.py` — BTC correlation filter + portfolio drawdown guard
- [x] Tests: 12 exchange + 21 indicators + 4 ceiling enforcement

### Phase 3: Pollers
- [x] `poller/base.py` — retry with exponential backoff, health heartbeat JSON, cycle timing
- [x] `poller/public/` — loads pairs from DB, defensive `_to_decimal()`, exchange-agnostic
- [x] `poller/private/` — iterates all venue accounts, syncs balances, detects fills, daily fee sync
- [x] `poller/ta/` — intraday + daily TA, paper stop-loss monitoring, ohlcv_1m pruning
- [x] Docker Compose services with `trading` profile + local poller start/stop/status
- [x] Tests: 8 poller tests (retry, health, run loop)

### Phase 4: CLI Tools (40+ commands)
- [x] `cli/market.py` — add-asset/venue/mapping/network/account/pair, overview, price, ta, history, seed-daily, fetch-daily (CoinGecko), compute-daily-ta, backfill-daily-ta, sync-fees, coverage, poller-status
- [x] `cli/strategy.py` — list, create, view, history, update (SCD Type 2), activate, deactivate, set-mode
- [x] `cli/trade.py` — buy (guardrails + paper/live), sell (FIFO cost basis + P&L), cancel (DB + exchange), list-orders. `--live` flag, allowed pairs from DB
- [x] `cli/signals.py` — scan (strategy registry + intraday guards + fee check), check
- [x] `cli/portfolio.py` — balance, accounts, pnl, transfers, transfer, snapshot, benchmark, history, reconcile
- [x] `cli/backtest.py` — run, sweep (param grid), list, view. LATERAL join for multi-source OHLCV

### Phase 5: Strategies (6 types, 8 instances for BTC/ETH/SOL/XRP)
- [x] `strategies/momentum.py` — RSI oversold + EMA + ADX + volume + regime
- [x] `strategies/trend_follow.py` — ATR trailing stop, golden cross, breakout
- [x] `strategies/volatility_breakout.py` — BB/Keltner squeeze detection
- [x] `strategies/mean_reversion.py` — BB lower band + RSI in sideways regime
- [x] `strategies/rsi_divergence.py` — bullish RSI divergence reversal
- [x] `strategies/bollinger.py` — BB mean reversion baseline
- [x] Keltner Channels, squeeze detection, EMA(8), high_20d in custom JSONB
- [x] All params tuned per asset on 6-month data via param sweeps

### Phase 5: Skills + Tasks + Seeding
- [x] `0__task_management.md` — global skill: create, delegate, follow up tasks
- [x] `1__trading_signal_workflow.md` — hourly scan flow, decision logic
- [x] `1__trading_portfolio_management.md` — daily/weekly review, escalation
- [x] `1__trading_strategy_reference.md` — regime coverage, params, guardrails
- [x] 5 recurring tasks: ROB-010 to ROB-014 (hourly scan, daily P&L, daily data, weekly review, weekly backtest)
- [x] `scripts/seed-trading.py` — seeds all reference data + strategies in one command
- [x] Historical CSVs committed: BTC (5744d), ETH (3893d), SOL (2185d), XRP (4626d)
- [x] `make trading-setup` = seed + OHLCV import + TA backfill

### Live Exchange Verification
- [x] Crypto.com Exchange: balance sync from sub-account, order place + cancel
- [x] CoinGecko: daily OHLCV fetch (7-day tested, ongoing via ROB-012)
- [x] Fee sync from exchange API (daily via private poller)
- [x] Public poller: 1m candles accumulating for BTC/ETH/SOL/XRP

### Signal Architecture
- [x] Dual data source: CoinGecko (market-wide signals) + Exchange (venue-specific guards)
- [x] Intraday execution guards: venue RSI > 75, spread > 0.5%, volatility > 2× ATR
- [x] Fee profitability check: skip trades where target < round-trip fees
- [x] Portfolio filters: BTC correlation (RSI < 25 or regime < 15), drawdown > 15%

### Docker Deployment
- [x] Trading toolkit baked into agent Docker image at `/opt/inotagent-trading`
- [x] Robin's env vars (from `agents/robin/.env`) provide exchange credentials
- [x] Container `POSTGRES_HOST=postgres` overrides toolkit defaults
- [x] `make clean-slate` — one command, zero to fully operational
- [x] Removed legacy sed schema substitution from entrypoint (prevented `trading_platform` corruption)

### Migration + Infra
- [x] Consolidated all migrations into shared `infra/postgres/migrations/` (dbmate, 001-012)
- [x] Hardcoded schema names: `openvaia` + `trading_platform`
- [x] Default schema updated from `platform` → `openvaia` across all code
- [x] `TRADING_DB_ENV` in Makefile for consistent DB connection
- [x] Local poller management: `make trading-poller-start/stop/status/logs`

### Agent Docs
- [x] Robin AGENTS.md: trading ops, anti-hallucination rule, workspace paths, task delegation via tags
- [x] Robin TOOLS.md: 22 tools + trading CLI reference table
- [x] Ino AGENTS.md: anti-hallucination, workspace paths, removed peer agents
- [x] Ino TOOLS.md: 22 tools, updated workspace paths

### ES-0012 Spec Updates
- [x] `_usdt` → `_usd` (currency-agnostic)
- [x] Removed CODEOWNERS
- [x] Data source architecture, strategy portfolio, intraday guards
- [x] Monorepo structure, deployment model, env separation

### Other
- [x] `docs/plans/ES-0015__day_trading_toolkit.md` — future plan for intraday indicators + day trading strategies
- [x] `CLAUDE.md` updated: 105 skills, 12 migrations, trading toolkit line

### Phase 6: Paper Trading (in progress)
- [x] 8 strategies created and activated (all paper mode) for BTC/ETH/SOL/XRP
- [x] Robin running in Docker, executing signal scans
- [x] Pollers running locally, 1m data accumulating
- [ ] Monitor paper results for 1-2 weeks
- [ ] Human review → switch approved strategies to live
