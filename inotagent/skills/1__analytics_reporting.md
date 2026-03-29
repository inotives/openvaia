---
name: analytics_reporting
description: Dashboard design, KPI tracking, statistical analysis workflow, data visualization rules, and reporting templates
tags: [analytics, reporting, dashboards, data, kpis]
source: agency-agents/support/support-analytics-reporter
---

## Analytics Reporting

> ~1600 tokens

### Dashboard Design Principles

1. **One dashboard, one audience**: Executive dashboards differ from operational ones
2. **KPI hierarchy**: Lead with 3-5 top-level metrics, drill-down for detail
3. **Context always**: Show trend (vs last period), target, and benchmark alongside every metric
4. **Anomaly highlighting**: Auto-flag metrics outside normal range (> 2 std deviations)
5. **Actionable layout**: Group metrics by decision they inform, not by data source
6. **Refresh cadence**: Match update frequency to decision frequency (real-time for ops, weekly for strategy)

### KPI Tracking Framework

Define each KPI with:

```
Metric: [name]
Definition: [exact calculation, no ambiguity]
Data Source: [system of record]
Owner: [who is accountable]
Target: [specific threshold]
Frequency: [how often measured]
Trend Direction: [higher is better / lower is better]
Alert Threshold: [when to flag for attention]
```

**Common KPI categories**:
- Revenue: MRR, ARR, ARPU, revenue growth rate
- Customers: acquisition rate, churn rate, LTV, NPS
- Product: DAU/MAU ratio, feature adoption, time-to-value
- Operations: uptime, response time, cost per transaction
- Marketing: CAC, conversion rate, channel ROI

### Data Visualization Rules

| Data Type | Best Chart | Avoid |
|-----------|-----------|-------|
| Trend over time | Line chart | Pie chart |
| Part of whole | Stacked bar or treemap | 3D pie |
| Comparison | Horizontal bar | Radar chart |
| Distribution | Histogram or box plot | Table of raw numbers |
| Correlation | Scatter plot | Dual-axis line chart |
| Single KPI | Big number with trend arrow | Gauge (hard to read) |

**Formatting rules**:
- Y-axis starts at 0 for bar charts (avoid truncated axes)
- Max 5-7 series per chart (more = separate charts)
- Color: use consistent palette; red/green only for bad/good, never for categories
- Label directly on chart when possible (avoid separate legends)
- Title states the insight, not the metric name ("Revenue grew 23% QoQ" not "Revenue Q1-Q4")

### Statistical Analysis Workflow

1. **Define hypothesis**: What question are we answering? Null vs alternative hypothesis
2. **Validate data**: Check completeness, accuracy, outliers, sample size
3. **Choose method**: t-test (two groups), ANOVA (multiple groups), regression (relationships), chi-square (categorical)
4. **Set significance**: alpha = 0.05 standard; calculate required sample size for power >= 0.8
5. **Run analysis**: Report effect size + confidence interval, not just p-value
6. **Interpret**: Statistical significance != practical significance. A 0.1% lift can be significant with huge N but meaningless in practice

### Reporting Cadence

| Report | Audience | Frequency | Focus |
|--------|----------|-----------|-------|
| Executive summary | C-suite | Monthly | Top KPIs, strategic insights, decisions needed |
| Operational dashboard | Team leads | Weekly | Operational metrics, blockers, trends |
| Deep-dive analysis | Stakeholders | Ad hoc | Specific question with full methodology |
| Automated alerts | On-call / owners | Real-time | Threshold breaches, anomalies |

### Analysis Report Template

```
# [Analysis Name] - Business Intelligence Report

## Executive Summary
- Primary Insight: [most important finding with quantified impact]
- Statistical Confidence: [confidence level, sample size]
- Business Impact: [quantified revenue/cost/efficiency impact]

## Data Foundation
- Sources: [list with quality assessment]
- Sample Size: [n records, statistical power analysis]
- Time Period: [range with seasonality notes]
- Data Quality: [completeness %, known gaps]

## Analysis
- Methodology: [statistical methods with justification]
- Key Findings: [ordered by impact, each with confidence interval]
- Benchmark Comparison: [vs industry/internal/historical]

## Recommendations
1. [High Priority]: [action] - Expected impact: [quantified] - Timeline: [date]
2. [Medium Priority]: [action] - Expected impact: [quantified] - Timeline: [date]
3. [Long-term]: [action] - Expected impact: [quantified] - Timeline: [date]

## Measurement Plan
- Primary KPIs: [metrics + targets]
- Review cadence: [when to re-measure]
- Success criteria: [what "done" looks like]
```

### Customer Segmentation (RFM)

Score customers on Recency, Frequency, Monetary (1-5 each):
- **Champions** (5-5-5): Reward loyalty, ask for referrals
- **Loyal** (4-4-4): Nurture, recommend new products
- **At Risk** (low R, high F/M): Re-engagement campaigns, win-back offers
- **New** (high R, low F): Optimize onboarding, early engagement
