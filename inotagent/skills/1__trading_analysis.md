---
name: trading_analysis
description: Market monitoring, technical analysis, and portfolio alert workflows
tags: [finance, trading, market-analysis, portfolio]
source: awesome-openclaw-agents/finance/trading-bot
---

## Trading Analysis

> ~694 tokens

### Daily Monitoring Workflow

1. **Morning brief** — Portfolio value, daily P&L, overnight moves, key events today
2. **Intraday alerts** — Trigger on price thresholds, volume spikes, volatility events
3. **Market close summary** — Day's performance, notable moves, after-hours events
4. **Weekly review** — Weekly performance, allocation drift, upcoming events (earnings, dividends, macro)

### Alert Thresholds (Defaults)

| Metric | Threshold | Action |
|--------|-----------|--------|
| Daily price change | +/- 5% | Alert |
| Volume spike | 3x average | Alert |
| Portfolio drawdown | -10% | Alert |
| Earnings date | 2 days before | Reminder |
| 52-week high/low approach | Within 2% | Alert |

### Technical Analysis Checklist

When analyzing a position:

- **Trend:** Price vs 50-day and 200-day moving averages
- **Momentum:** RSI (overbought >70, oversold <30)
- **Volatility:** Bollinger Bands width, ATR
- **Volume:** Current vs average, confirmation of price moves
- **Support/Resistance:** Key price levels from recent history
- **MACD:** Signal line crossovers, divergence from price

### Position Analysis Template

```
Position: <shares/amount> <symbol> @ <avg_cost>
Current: <price> (<pct_change>, <dollar_pnl>)

Technical:
- RSI: <value> (<interpretation>)
- 50-day MA: <value> (price <above/below>)
- Resistance: <level>
- Support: <level>

Fundamentals:
- P/E: <value> (vs 5yr avg)
- Next earnings: <date>
- Analyst consensus: <target> (<pct upside/downside>)

Options:
1. Hold — <reasoning>
2. Trim — <reasoning>
3. Exit — <reasoning>
```

### Data Quality Rules

- Always include data source and timestamp with market data
- If data is stale (>15 min for crypto, >1 min for stocks during market hours), flag it clearly
- Distinguish between analysis/opinion and factual data
- Never guarantee returns or make profit predictions
- Include risk disclaimers when discussing specific trades
- Never execute trades without explicit user confirmation

### Portfolio Summary Format

```
Portfolio: $<total> (<daily_pct> today, <ytd_pct> YTD)

| Position | Price | Daily | P&L |
|----------|-------|-------|-----|
| <symbol> | <price> | <pct> | <dollar> |

Key Events Today:
- <event with time>

Alerts:
- <active alerts>
```

### Sentiment Sources

- Earnings reports (EPS actual vs estimate, guidance)
- Financial news feeds
- Social media sentiment (Reddit, Twitter/X)
- ETF flow data
- Fed/central bank statements and minutes
- Macro economic indicators (CPI, jobs, GDP)
