---
name: trading_portfolio_management
description: Daily/weekly portfolio review, P&L tracking, strategy performance monitoring
tags: [trading, portfolio, review]
---

## Trading Portfolio Management

> Equip this skill for daily P&L reviews, weekly strategy evaluation, and portfolio monitoring.

### CLI Path
All commands: `shell("cd /opt/inotagent-trading && python -m cli.<module> <command>")`

### Daily Routine (recurring task, ~10:00 UTC)

```
1. Market overview
   cli.market overview
   → Check: current prices, regime score, key TA levels

2. Portfolio balance
   cli.portfolio balance
   → Check: total balance, positions across venues

3. Today's P&L
   cli.portfolio pnl --period today
   → Report: total_pnl, trades, win/loss count, fees

4. Open positions
   cli.trade list-orders --status open
   cli.trade list-orders --status filled
   → Check: any orders that should have been cancelled? Stale positions?

5. Take daily snapshot
   cli.portfolio snapshot
   → Records daily portfolio value for historical tracking

6. Report to Discord
   Post: "Daily P&L: $X (+Y%), Z trades today. Portfolio: $TOTAL."
```

### Weekly Review (recurring task, Sunday ~12:00 UTC)

```
1. Weekly performance
   cli.portfolio pnl --period week
   cli.portfolio benchmark --days 7

2. Strategy-level analysis
   For each active strategy, review:
   - How many trades this week?
   - Win rate trending up or down?
   - Any consecutive losses (3+)?

3. Anomaly detection
   - 3+ consecutive losses on any strategy → deactivate and report
   - Daily loss > 3% of portfolio → pause all and report
   - Strategy win rate < 30% over last 10 trades → recommend deactivation

4. Backtest re-run (monthly or when performance degrades)
   cli.backtest run --strategy <name> --from <12mo_ago> --to today
   → Compare backtest prediction vs actual results
   → If divergence > 10% → investigate

5. Report to Discord
   Post weekly summary:
   - Total P&L (week + cumulative)
   - Best/worst strategy
   - Recommendations (param adjustments, activation changes)
   - "CONTINUE / PAUSE / ADJUST" for each strategy
```

### Strategy Param Tuning
You CAN freely tune params in paper mode:
```
cli.strategy update --name cro_momentum --param entry.rsi_buy_threshold=30
```
This creates a new SCD Type 2 version. The old version is preserved.

For live strategies, **report to Boss first** with reasoning:
```
"cro_momentum win rate dropped from 60% to 35% this week.
 RSI threshold 35 may be too aggressive in current market.
 Recommend: lower to 30. Testing in paper mode first."
```

### Strategy Lifecycle Commands
```
cli.strategy list                          → all strategies + status
cli.strategy view --name <name>            → full params
cli.strategy history --name <name>         → version history
cli.strategy activate --name <name>        → enable for signal scanning
cli.strategy deactivate --name <name>      → disable
cli.strategy set-mode --name <name> --mode paper|live  → Boss only for live
```

### Transfer & Reconciliation
```
cli.portfolio transfers --days 30          → transfer history
cli.portfolio reconcile-pnl --days 30     → check P&L vs balance changes
cli.portfolio accounts                     → list all accounts + balances
```

### Escalation Rules
Report to Boss immediately via Discord when:
- Daily loss exceeds 5% of portfolio
- A strategy has 3+ consecutive losses
- Balance discrepancy detected in reconciliation
- BTC correlation filter blocks signals for 3+ consecutive days
- Any trade exceeds the human approval threshold (20% of portfolio)
