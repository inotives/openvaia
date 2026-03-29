---
name: fraud_detection
description: Monitor transactions for fraud patterns, score risk levels, and generate daily fraud summaries.
tags: [finance, fraud, security, monitoring]
source: awesome-openclaw-agents/agents/finance/fraud-detector
---

## Fraud Detection

> ~601 tokens

### Risk Scoring Framework

Score transactions by risk level with reasoning:

| Risk Level | Score Range | Action |
|------------|------------|--------|
| Low | 0-30% | Auto-approve, log |
| Medium | 31-60% | Flag for review |
| High | 61-85% | Hold, request verification |
| Critical | 86-100% | Block, escalate immediately |

### Red Flag Signals

| Signal | Description | Weight |
|--------|-------------|--------|
| Geographic anomaly | Transaction location inconsistent with history | High |
| Amount spike | Transaction > 3x average for this account | High |
| Velocity spike | Unusual number of transactions in short window | High |
| High-risk merchant | Categories commonly used in fraud (electronics, gift cards) | Medium |
| Failed payment sequence | Multiple failed attempts before success | Medium |
| Card testing | Small-value transactions ($1-$5) at gas stations | Medium |
| Impossible travel | Transactions in distant locations within short time | Critical |
| Device change | New device/browser with high-value transaction | Medium |

### Transaction Risk Assessment Format

```
Transaction Risk Assessment

| Field | Value |
|-------|-------|
| Amount | $<amount> |
| Merchant | <name> |
| Location | <location> |
| Card | ****<last4> |
| Risk Score | <LEVEL> (<percent>%) |

Red Flags:
1. <signal> -- <evidence>
2. <signal> -- <evidence>

Recommendation: <action>
```

### Daily Fraud Summary Format

```
Daily Fraud Summary -- <date>

| Metric | Value | vs. Yesterday |
|--------|-------|---------------|
| Transactions Scanned | <N> | <change> |
| Alerts Generated | <N> | <change> |
| Critical Alerts | <N> | <change> |
| Confirmed Fraud | <N> | -- |
| False Positive Rate | <percent>% | <change> |
| Total Value Flagged | $<amount> | <change> |

Critical Alerts:
1. <card> -- <description>. Status: <status>.

Pattern of the Day:
<notable pattern observed>
```

### Rules

- Never auto-block a transaction without providing a risk score and reasoning
- Always include a confidence percentage with fraud alerts
- Escalate critical-risk transactions immediately with full context
- Never expose raw customer financial data -- use masked formats (****1234)
- Minimize false positives by cross-referencing multiple signals before flagging
- Present findings objectively; let the human reviewer make the final call
