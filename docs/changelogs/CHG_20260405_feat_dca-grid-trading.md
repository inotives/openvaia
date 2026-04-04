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
