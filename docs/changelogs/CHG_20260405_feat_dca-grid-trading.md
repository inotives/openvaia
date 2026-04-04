# Changelog: feature/dca-grid-trading

**Branch**: `feature/dca-grid-trading`
**Created**: 2026-04-05
**ES Plan**: ES-0016 — DCA Grid + Regime Trading on Crypto.com

## Summary

DCA Grid trading with two modes (Batch Grid + Adaptive FIFO Grid), regime-based switching, sentiment integration, maker-only execution, and exchange-side stop-loss.

## Changes

### Phase 1: Batch Grid Engine + BTC Grid
- [x] `strategies/dca_grid.py` — grid level computation (ATR-based spacing, weighted capital allocation)
- [x] Grid cycle state management (GridLevel, GridCycle dataclasses)
- [x] Mode selection: Batch (RS 0-30) / Adaptive FIFO (RS 30-60) with auto-selection
- [x] Entry conditions: regime with hysteresis (pause 65, resume 55), RSI, ATR, active cycle check, expired cap
- [x] Volatility regime detection (low/normal/high/extreme) with per-regime params
- [x] TP computation: batch (weighted avg + target + fees), FIFO (per-level + fees)
- [x] `cli/grid.py` — new CLI module: open (places 5 maker limit orders), status, cancel
- [x] `tests/test_dca_grid.py` — 27 tests (levels, weights, mode, hysteresis, TP, entry conditions)
- [x] `btc_dca_grid` strategy added to seed script with default params
- [x] Verified: open cycle → check status → cancel cycle against local DB

### Phase 2: Adaptive FIFO Mode + Regime Integration + Monitor
- [x] `cli/grid.py monitor` — main grid loop: fill detection, TP placement, regime transitions, expiry
- [x] FIFO mode: per-level individual TP sell orders placed on fill detection
- [x] Batch mode: single TP updated (cancel + replace) as levels fill
- [x] Paper fill simulation: detects when current price <= grid level price
- [x] Paper TP detection: detects when current price >= TP price
- [x] Regime transition: RS >= 65 → cancel unfilled, keep TPs, mark transition_pending
- [x] Stop-loss detection: current price <= stop → close cycle, cancel all orders
- [x] Cycle expiry: 72h → cancel unfilled, mark expired_pending
- [x] All TP sold detection: closes cycle when all filled levels are sold (FIFO)

### Phase 3: Sentiment Integration
- [x] `core/sentiment.py` — sentiment score computation (FGI + funding rate + news)
- [x] `cli/market.py fetch-sentiment` — fetches Fear & Greed Index from API, stores in indicators_daily.custom
- [x] Private poller `_sync_funding_rates()` — fetches BTC/ETH perp funding rates, stores in indicators_intraday.custom
- [x] Grid `open` command: loads sentiment, adjusts capital (0x-1.5x), skips on extreme greed
- [x] Sentiment helpers: normalize_fear_greed, normalize_funding_rate, get_sentiment_adjustments
- [x] Verified: FGI=11 (extreme fear) fetched and stored, sentiment score computed correctly

### Phase 3.5: Sentiment Gaps + Migration Fix
- [x] Funding rate: loads perp pairs from DB (not hardcoded), derives from spot if no explicit perps
- [x] Perp pairs seeded: BTC/ETH/SOL/XRP USD:USD with perp fees (0.015%/0.045%)
- [x] Migration 013: fix trading_pairs unique constraint to include pair_symbol (allows spot + perp same base/quote)
- [x] `1__trading_sentiment_analysis.md` — skill for Robin to score daily news sentiment (-1.0 to +1.0)
- [x] `core/sentiment.py` — store_sentiment_snapshot + get_sentiment_trend (7d history)
- [x] `cli/market.py sentiment` — show composite score, components, adjustments, 7d trend
- [x] `cli/market.py sentiment --news-score -0.5` — Robin stores its news analysis score
- [x] Grid monitoring moved to TA poller (60s, no LLM) — Robin only handles decisions hourly
- [x] ROB-010 reverted to hourly: opens new cycles, regime transitions, signal scan (LLM-worthy)
- [x] TA poller handles: fill detection, TP placement, stop-loss, expiry (mechanical, no LLM)
- [x] Grid monitoring moved to TA poller (60s, no LLM) — fills, TPs, stop-loss, expiry
- [x] ROB-010 reverted to hourly — Robin handles decisions (open cycles, regime, signals)
- [x] Poller resilience: all 3 pollers run each step independently (one failure doesn't block others)
- [x] Public poller: continues to next pair on failure instead of aborting cycle
- [x] Updated all Robin tasks for DCA grid as primary strategy + UTC times
- [x] Updated skill chains: trading_analysis + trading_execution use new skill names

### Phase 4: Multi-Asset + Defensive Mode
- [x] Seeded grid strategies: eth_dca_grid, sol_dca_grid, xrp_dca_grid with per-asset tuning
- [x] Per-asset params: ETH (8% ATR max, 1.5-2.5% target), SOL/XRP (10% ATR, 2-3.5% target, 8% capital)
- [x] Defensive grid mode: when normal entry fails but RSI deeply oversold, opens wider/safer grid
- [x] Defensive overrides: 0.8x ATR spacing, 2.5% target, equal weights [1,1,1,1,1]
- [x] should_open_cycle returns (can, reason, is_defensive) — 3 values
- [x] create_cycle accepts defensive=True for wider params
- [x] BTC defensive enabled in seed script
- [x] Tests: 30 grid tests (3 new: defensive activate, not enabled, wider grid)
- [x] Entrypoint: removed migration from Docker (run from host only via `make local-migrate`)
- [x] `clean-slate`: runs migrations from host before deploying containers
