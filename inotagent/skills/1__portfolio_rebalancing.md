---
name: portfolio_rebalancing
description: Portfolio allocation analysis, drift detection, rebalancing trades, and diversification scoring
tags: [finance, portfolio, investing, rebalancing]
source: awesome-openclaw-agents/finance/portfolio-rebalancer
---

## Portfolio Rebalancing

> ~711 tokens

### Rebalancing Workflow

1. **Calculate current allocation** — Current value of each position as % of total portfolio
2. **Compare to target** — Compute drift (current % - target %) for each asset class
3. **Apply threshold** — Only rebalance positions with drift exceeding threshold (typically 5%)
4. **Generate trades** — Calculate buy/sell amounts to restore target weights
5. **Tax review** — Check for tax implications before executing
6. **Minimize transactions** — Optimize for fewest trades (reduce costs and tax events)

### Drift Analysis Table

```
| Asset | Current % | Target % | Drift | Action |
|-------|-----------|----------|-------|--------|
| <asset> | <pct> | <pct> | <+/- pct> | Buy/Sell/Hold |
```

Threshold rule: Only generate trades when drift exceeds the rebalancing threshold. Skip trivial adjustments.

### Tax Considerations Checklist

- [ ] Check holding period: long-term (>1 year) vs short-term capital gains
- [ ] Identify tax lots — sell highest-cost-basis lots first to minimize gains
- [ ] Look for tax-loss harvesting opportunities (sell losers to offset gains)
- [ ] Check wash sale rule: no repurchase of substantially identical security within 30 days
- [ ] Consider year-end timing: defer gains to next tax year if close to Dec 31
- [ ] Estimate tax impact before recommending trades

### Diversification Scoring

Score portfolio on these dimensions (1-10 each):

| Factor | What to Check |
|--------|--------------|
| Asset class mix | Spread across equities, bonds, alternatives, cash |
| Geographic diversity | Domestic vs international allocation |
| Sector concentration | Exposure spread across sectors |
| Correlation | How correlated are the holdings? High correlation = less true diversification |
| Single position risk | Any single holding >10% of portfolio is a concentration risk |

### Concentration Rules

- Flag any single holding over 10% of total portfolio
- Flag any single sector over 30% of equity allocation
- Flag geographic allocation deviating >15% from global market cap weights
- Flag bond allocation below age-appropriate minimum (rough rule: age - 10 = bond %)

### Rebalancing Methods

**Threshold-based** — Rebalance when any asset drifts beyond a set % (e.g., 5%). Most common.

**Calendar-based** — Rebalance on fixed schedule (quarterly, annually). Simple but may miss large drifts.

**Cash-flow based** — Direct new contributions to underweight assets. Minimizes selling and tax events.

**Band-based** — Each asset has its own tolerance band based on volatility. Wider bands for volatile assets.

### Output Format

```
### Recommended Trades
1. <Buy/Sell> $<amount> <symbol> — <reasoning>

### Tax Considerations
- <relevant tax notes>

### Post-Rebalance Allocation
| Asset | New % | Target % |
```

Always include disclaimer: "This is portfolio analysis, not financial advice."
