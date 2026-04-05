# Changelog: feature/dca-grid-trading

**Branch**: `feature/dca-grid-trading`
**Created**: 2026-04-05
**ES Plan**: ES-0016 — DCA Grid + Regime Trading on Crypto.com

## Summary

Full regime-based trading system: DCA Grid (bear/ranging) + Pyramid Trend (bull, BTC/ETH) + Trend Follow (bull, XRP). Includes sentiment integration, maker-only execution, composite backtester, CoinGecko universe sync, and clean-slate deployment pipeline.

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

### Phase 5: Grid Backtesting
- [x] `cli/backtest_grid.py` — grid-specific backtester using daily high/low for fill simulation
- [x] Multi-order simulation: 5 limit orders per cycle, fills when daily low <= grid price
- [x] TP simulation: batch (high >= avg + target) and FIFO (high >= level + target)
- [x] Cycle lifecycle: open → fill → TP/stop/expire → close → cooldown → next
- [x] Capital accounting: unfilled levels return capital on cancel/expire/regime transition
- [x] Backtested 6 months (2025-10 to 2026-03): all 4 assets show +34-62% alpha vs HODL
- [x] ETH/SOL net positive (+0.1-0.4%) in -50-62% bear market
- [x] Entrypoint: removed migration from Docker (run from host only via `make local-migrate`)
- [x] `clean-slate`: runs migrations from host before deploying containers

### Phase 5.5: Strategy Param Tuning
- [x] Grid param sweep: tighter ATR spacing (0.15x-0.3x) outperforms default (0.4x-0.8x)
- [x] BTC grid: 0.15x ATR low/normal, 0.3x high — more cycles, better fill rate
- [x] ETH grid: 0.15x low, 0.2x normal, 0.4x high
- [x] SOL/XRP grid: 0.2x low, 0.3x normal, 0.5x high
- [x] BTC defensive mode enabled in seed
- [x] Trend follow re-tuned on bull period (Jun 2024 - Nov 2025)
- [x] BTC trend: RS>40, ADX>15, trail 4.0x ATR (+7.1% bull, was -6.1%)
- [x] ETH trend: RS>61, ADX>25, trail 2.0x ATR (+0.3% bull)
- [x] SOL trend: RS>50, ADX>15, trail 2.0x ATR (-0.8% bull)
- [x] XRP trend: RS>50, ADX>15, trail 3.0x ATR (+41.7% bull)
- [x] Seed script updated with all tuned params (grid + trend follow)

### Phase 5.5b: Pyramid Trend Strategy
- [x] `strategies/pyramid_trend.py` — scale into winners with asymmetric LIFO exits
- [x] 4 lots: A (40%, exits on regime flip) → B (30%, 12-15% trail) → C (20%, 10% trail) → D (10%, 5% trail)
- [x] Entry: 20d high breakout + golden cross + ADX + RSI < 75, min 4/5 conditions
- [x] Pyramiding: add lots at +3-5% (B), +12% (C), +20% (D) from base entry
- [x] Hard stop: 5% below base entry exits all lots
- [x] Per-lot exit conditions: D (tight trail/RSI), C (medium trail/MACD), B (loose trail/EMA50), A (regime flip)
- [x] Pyramid backtester in `cli/backtest.py` — multi-lot position tracking with LIFO exits
- [x] Tuned: BTC (DT:5%, CT:10%, BT:12%, exit RS<45), ETH (BT:15%, pyramid B@+3%)
- [x] BTC: +4.9% bull (65% WR), ETH: +6.8% burst period (77% WR)
- [x] Seeded: btc/eth_pyramid_trend with tuned params, sol/xrp_pyramid_trend (inactive)

### Phase 5.5c: Volatility Breakout Strategy
- [x] Seeded: btc/eth/sol/xrp_volatility_breakout — BB squeeze → breakout + volume confirmation
- [x] Supplementary role — low trade count but high quality signals

### Phase 6: Composite Backtester + Regime Switching
- [x] `cli/backtest_composite.py` — full regime-switching backtest across strategies
- [x] RS 0-65: DCA Grid, RS 65+: Pyramid Trend (BTC/ETH) or Trend Follow (XRP)
- [x] SOL set to grid-only — trend follow disabled (was -$117 drag, now +1.0%)
- [x] Compounding enabled by default — matches live system (uses current equity as capital base)
- [x] Full period results (22mo): BTC +9.2%, ETH +6.7%, SOL +1.0%, XRP +39.3%
- [x] Bear period (5mo): all 4 assets positive alpha (+41-55%), zero trend trades, grid-only
- [x] 20 strategies seeded across 5 types × 4 assets

### Phase 7: Data Pipeline + Deployment Fixes
- [x] `cli.market sync-coingecko` — syncs 17,839 coins + 444 platforms into ext_coingecko_assets/platforms
- [x] `cli.market fetch-daily` — volume from `/coins/markets` attached to yesterday's completed day
- [x] CoinGecko API key support (`x_cg_demo_api_key` header) — 30 calls/min vs 10/min
- [x] Skip today's partial OHLC candle — only upsert completed days
- [x] `fetch-daily --days` accepts CoinGecko valid values: 1, 7, 14, 30, 90, 180, 365
- [x] `wipe-db` drops both `openvaia` and `trading_platform` schemas
- [x] Pollers added to `infra` profile — start automatically with `deploy-all` / `clean-slate`
- [x] Poller Dockerfile: added `.venv/bin` to PATH (fix `No module 'pandas'` crash)
- [x] Agents container: added `inotagent-trading/.env` as second env_file (exchange + CoinGecko keys)
- [x] `clean-slate` pipeline: build infra profile images before starting containers
- [x] `trading-setup` pipeline: seed → sync-coingecko → seed-ohlcv → fetch-daily → backfill-ta
- [x] Makefile: `trading-sync-coingecko`, `trading-fetch-daily DAYS=N` targets added
