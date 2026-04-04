# Changelog: feature/dca-grid-trading

**Branch**: `feature/dca-grid-trading`
**Created**: 2026-04-05
**ES Plan**: ES-0016 — DCA Grid + Regime Trading on Crypto.com

## Summary

DCA Grid trading with two modes (Batch Grid + Adaptive FIFO Grid), regime-based switching, sentiment integration, maker-only execution, and exchange-side stop-loss.

## Changes

### Phase 1: Batch Grid Engine + BTC Grid
- [ ] Create `strategies/dca_grid.py` — grid level calculation, Batch mode cycle state
- [ ] Create grid cycle manager — open/fill/close/cancel lifecycle
- [ ] Update `cli/trade.py` — multiple limit orders + cancel-all-for-cycle
- [ ] Create `btc_dca_grid` strategy with Batch mode defaults
- [ ] Paper test: place grid orders, verify fills, batch take-profit
