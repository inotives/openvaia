---
name: financial_forecasting
description: Revenue/expense forecasting with scenario modeling, runway analysis, and variance tracking
tags: [finance, forecasting, planning, analysis]
source: awesome-openclaw-agents/finance/financial-forecaster
---

## Financial Forecasting

> ~770 tokens

### Forecasting Workflow

1. **Gather historical data** — Minimum 3-6 months for trends, 12+ months for seasonality
2. **Check data quality** — Flag missing months, outliers, one-time events that skew trends
3. **Identify growth pattern** — Linear, accelerating, decelerating, seasonal, or flat
4. **State assumptions explicitly** — Every forecast must list its key assumptions
5. **Build three scenarios** — Best case, base case, worst case
6. **Present ranges, not point estimates** — Use confidence intervals

### Scenario Modeling

Always provide three scenarios:

| Scenario | When to Use | Assumptions |
|----------|------------|-------------|
| **Best case** | Optimistic but plausible | Favorable market, strong execution, growth accelerates |
| **Base case** | Most likely outcome | Current trends continue, no major changes |
| **Worst case** | Realistic downside | Increased churn, slower growth, market headwinds |

For each scenario, document:
- Growth rate assumption and rationale
- Key risk or catalyst that would trigger this scenario
- Impact on bottom line (revenue, burn, runway)

### Key Metrics to Track

**SaaS / Subscription**
- MRR / ARR (Monthly / Annual Recurring Revenue)
- MoM growth rate and trend (accelerating vs decelerating)
- Churn rate (logo churn and revenue churn)
- Net revenue retention
- CAC and LTV

**Startup / Burn Rate**
- Cash on hand
- Monthly gross burn (total expenses)
- Monthly net burn (expenses minus revenue)
- Runway = Cash / Net Burn (in months)

**Unit Economics**
- Revenue per customer / user
- Cost per acquisition
- Gross margin
- Payback period

### Runway Analysis Template

```
| Metric | Value |
|--------|-------|
| Cash on hand | $<amount> |
| Monthly burn | $<amount> |
| Monthly revenue | $<amount> |
| Net burn | $<amount>/mo |
| Runway | <months> months |

Scenario table:
| If Revenue... | Net Burn | Runway |
|---------------|----------|--------|
| Stays flat | $<x> | <y> months |
| Grows <n>% MoM | Break-even by <date> | Infinite |
| Drops <n>% | $<x> | <y> months |
| Zero revenue | $<x> | <y> months |
```

### Variance Analysis

When comparing actuals vs forecast:

1. Calculate variance: `(Actual - Forecast) / Forecast * 100`
2. Flag variances exceeding +/- 10%
3. Categorize: timing (shifted between months), volume (more/fewer units), price (rate change), or one-time event
4. Update forecast assumptions based on actuals

### Forecasting Rules

- Always state assumptions explicitly — a forecast without assumptions is just a guess
- Use ranges, not single-point estimates
- Never present projections as guarantees — label as estimates
- Use consistent time periods when comparing data (MoM, QoQ, YoY)
- Flag data quality issues before forecasting (missing data, outliers)
- Round to appropriate precision — no cents on million-dollar forecasts
- Separate recurring vs one-time revenue/expenses
- Adjust for seasonality when historical data supports it
