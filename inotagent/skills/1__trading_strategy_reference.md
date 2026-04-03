---
name: trading_strategy_reference
description: Strategy details, regime coverage, param reference for inotagent-trading
tags: [trading, strategy, reference]
---

## Trading Strategy Reference

> Reference for all trading strategies, their params, and how they interact.

### Regime Score (0-100)
Computed daily from three components:
- **ADX(14)** × 0.4 — trend strength (15→0, 25→50, 40→100)
- **EMA50 slope 5d%** × 0.4 — trend direction (0%→0, 0.5%→100)
- **Volatility ratio** × 0.2 — noise filter, inverted (1.2→0, 0.8→100)

| Regime | Market State | Active Strategies |
|--------|-------------|-------------------|
| 0-15 | Crash | None — all idle |
| 15-25 | Deep sideways | mean_reversion |
| 25-35 | Sideways/transition | mean_reversion, rsi_divergence |
| 35-50 | Moderate | rsi_divergence, momentum |
| 50-60 | Strong moderate | momentum |
| 61+ | Strong trend | trend_follow |
| Any (squeeze) | Volatility compression | volatility_breakout (scout) |

### Strategy Details

**1. Trend Follow** (`cro_trend_follow`, regime 61+)
- Entry: regime >= 61, golden cross (EMA50 > EMA200), price > 5d high, ADX >= 25, RSI < 70
- Exit: ATR trailing stop (3× ATR from highest), initial stop (2× ATR from entry)
- Size: 15%, risk 1% per trade
- Catches big moves, few trades, large wins

**2. Momentum** (`cro_momentum`, regime 40-60)
- Entry: RSI < 35 (oversold), ADX > 15, regime > 40, volume > 1.5×
- Exit: +8% take profit, -5% stop loss
- Size: 10%
- Workhorse — most active, consistent small gains

**3. Volatility Breakout / Scout** (`cro_scout`, squeeze)
- Entry: BB inside Keltner (squeeze), price breaks above BB upper + 20d high, ADX < 20, RVOL > 2×
- Exit: -1.5× ATR stop, trail via EMA(8), 3-day time stop
- Size: 5% (small — higher false breakout risk)
- Rare but high conviction. Gets in before trend follow signals.

**4. RSI Divergence** (`cro_divergence`, regime 25-50)
- Entry: price lower low + RSI higher low (bullish divergence), RSI < 35, regime 25-50
- Exit: RSI > 55 (recovered), or EMA(20) reached, -3% stop, 5-day time stop
- Size: 10%
- Catches reversals that momentum misses

**5. Mean Reversion** (`cro_mean_revert`, regime 15-35)
- Entry: close below BB lower, RSI < 30 turning up, regime 15-35, ATR% stable
- Exit: price reaches SMA(20), -2% hard stop, 2-day time stop
- Size: 12%
- Range trading — quick in, quick out

**6. Bollinger** (`cro_bollinger`, disabled by default)
- Entry: close near/below BB lower, RSI < 40, BB width > 2%, volume > 0.8×
- Exit: middle band or upper band, -5% stop
- Baseline strategy — mean_reversion is the improved version

### Portfolio Filters (block ALL buy signals)
- **BTC correlation**: if BTC RSI < 25 or BTC regime < 15 → all buys paused
- **Portfolio drawdown**: if portfolio down > 15% from peak → all buys paused

### Guardrails (enforced by CLI, cannot be overridden)
- Max 10% of portfolio per trade
- Max 3 open positions
- Stop-loss required on every buy
- Stop-loss cannot be wider than 8%
- Minimum trade size $5
- Trades > 20% need human approval
- Only approved pairs (CRO/USDT)
- Paper mode default for new strategies
