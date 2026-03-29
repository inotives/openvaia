---
name: revenue_analysis
description: Track MRR/ARR, analyze churn, forecast revenue, and calculate unit economics for SaaS businesses.
tags: [finance, revenue, saas, metrics]
source: awesome-openclaw-agents/agents/finance/revenue-analyst
---

## Revenue Analysis

> ~611 tokens

### MRR Decomposition

Break down Monthly Recurring Revenue into components:

| Component | Description |
|-----------|-------------|
| New MRR | Revenue from new customers |
| Expansion MRR | Revenue from upgrades and add-ons |
| Contraction MRR | Revenue lost from downgrades |
| Churn MRR | Revenue lost from cancellations |
| Reactivation MRR | Revenue from returning customers |
| **Net New MRR** | Sum of all components |

### MRR Report Format

```
MRR Report -- <month>

Current MRR: $<amount>
MRR Growth: +/-$<amount> (+/-<percent>% MoM)

MRR Movements:
| Component | Amount | Count |
|-----------|--------|-------|

Key Metrics:
| Metric | Current | Last Month | Trend |
|--------|---------|------------|-------|
| Gross Churn | <percent>% | | |
| Net Revenue Retention | <percent>% | | |
| ARPU | $<amount> | | |
| Customer Count | <N> | | |
```

### Churn Analysis Framework

Analyze churn by:
- **By plan tier:** Identify which plans have highest churn rates
- **By cohort age:** When do customers churn (month 1-3 vs. 6-12 vs. 12+)?
- **By reason:** Categorize cancellation survey responses
- **Revenue vs. logo churn:** Losing many small accounts vs. few large ones

### Unit Economics

| Metric | Formula |
|--------|---------|
| LTV (Lifetime Value) | ARPU / Monthly Churn Rate |
| CAC (Customer Acquisition Cost) | Total Sales+Marketing Spend / New Customers |
| LTV:CAC Ratio | LTV / CAC (healthy: > 3:1) |
| Payback Period | CAC / Monthly ARPU |

### Revenue Forecasting

- Trend extrapolation from historical MRR growth rate
- Scenario modeling (optimistic/base/pessimistic)
- Factor in known pipeline and seasonal patterns
- Flag when sample sizes are too small for reliable conclusions

### Cohort Retention Analysis

Track retention by signup cohort:
- Month 1, 3, 6, 12 retention rates
- Revenue retention vs. logo retention
- Identify improving or declining cohort trends

### Rules

- Always specify the time period and whether numbers are MRR or ARR
- Show both absolute numbers and percentage changes
- Include the "why" behind metric movements, not just the "what"
- Always flag when sample sizes are too small for reliable conclusions
- Connect metrics to business outcomes and actionable insights
