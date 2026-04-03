---
name: trading_signal_workflow
description: Hourly signal scan, trade decision logic, order execution for inotagent-trading
tags: [trading, signals, execution]
---

## Trading Signal Workflow

> Equip this skill for hourly signal scanning and trade execution.

### CLI Path
All commands: `shell("cd /opt/inotagent-trading && python -m cli.<module> <command>")`

### Hourly Scan (every hour)

```
Step 1: Scan signals
  cli.signals scan

Step 2: Interpret output
  signals[]       → actionable buy signals with confidence + suggested_action
  no_signal[]     → strategies that evaluated but found nothing (normal)
  filters[]       → portfolio-level blocks (BTC crash, drawdown) — DO NOT trade
  blocked[]       → signals that were blocked by filters

Step 3: Decision
  If filters non-empty → report to Discord, wait. Do NOT override.
  If signals empty → log, move on.
  If signal found → continue to Step 4.

Step 4: Pre-trade checks
  cli.trade list-orders --status open
  - Already have open position in this asset? → skip (avoid doubling up)
  - Confidence >= 0.70? → full position
  - Confidence 0.50-0.69? → half position or skip
  - Confidence < 0.50? → never trade

Step 5: Execute
  cli.trade buy --symbol CRO --venue cryptocom \
    --amount <usd> --price <price> --stop-loss <sl> \
    --strategy <name> --rationale "<paste signal reasons>"

Step 6: Report
  Post to Discord: "Bought <qty> CRO @ $<price>, stop-loss $<sl>, strategy: <name>, confidence: <conf>"
```

### Strategy Table (regime-based, all run simultaneously)

| Strategy | Regime | Size | Description |
|----------|--------|------|-------------|
| cro_trend_follow | 61+ | 15% | Ride uptrends with ATR trailing stop |
| cro_momentum | 40-60 | 10% | Buy RSI oversold dips |
| cro_scout | Squeeze | 5% | Catch breakouts at volatility squeeze release |
| cro_divergence | 25-50 | 10% | RSI bullish divergence reversal |
| cro_mean_revert | 15-35 | 12% | Range trade at BB lower band |

Crash regime (0-15): ALL idle — do not trade.

### Exit Monitoring
Stops are handled automatically:
- **Paper mode**: TA poller monitors stop-loss
- **Live mode**: exchange stop orders or poller monitoring

But check daily:
- Time stops: scout (3d), mean_revert (2d), divergence (5d) — exit if held too long with no profit
- Regime change: if regime dropped out of strategy's range, consider manual exit

### Key Rules
- **Paper mode first** — all strategies start paper. Only Boss switches to live.
- **One signal → one trade** — don't stack multiple buys on the same signal.
- **Guardrails are enforced** — the CLI rejects trades that violate limits. Trust them.
- **Always include rationale** — paste the signal reasons into --rationale for audit trail.
