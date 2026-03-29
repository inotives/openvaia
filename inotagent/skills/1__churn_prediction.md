---
name: churn_prediction
description: Score accounts by churn risk, detect early warning signals, and recommend targeted retention actions.
tags: [business, churn, retention, saas]
source: awesome-openclaw-agents/agents/business/churn-predictor
---

## Churn Prediction

> ~650 tokens

### Churn Risk Scoring (0-100)

| Score | Risk Level | Action |
|-------|-----------|--------|
| 80-100 | High | Personal outreach, retention offer |
| 50-79 | Medium | Automated re-engagement |
| 0-49 | Healthy | Standard nurture |

### Early Warning Signals

| Signal | Threshold | Weight |
|--------|-----------|--------|
| Login inactivity | 7+ days (was daily user) | High |
| Usage drop | >50% decrease over 2 weeks | High |
| Failed payments | 2+ consecutive failures | High |
| Support ticket sentiment | Negative tone about pricing/value | Medium |
| Feature downgrade | Removed features or seats | Medium |
| Session duration drop | >40% decrease from average | Medium |

### Churn Risk Report Format

```
Weekly Churn Risk -- <date range>

High Risk (score 80+): <N> accounts
1. <name> (score: <N>) - $<MRR>/mo
   Signal: <key behavioral indicator>
   Action: <recommended intervention>

Medium Risk (score 50-79): <N> accounts
Revenue at risk: $<amount>/mo

Healthy: <N> accounts (<percent>% of base)
```

### Churn Analysis Framework

Analyze churned customers by:
- **Reason:** Too expensive, competitor, not using, missing features, payment failed
- **Cohort age:** Month 0-3 (onboarding gap), 3-6, 6-12, 12+
- **Plan tier:** Which plans churn fastest
- **Revenue impact:** Total MRR lost, average customer lifetime

### Retention Action Playbook

| Risk Signal | Recommended Action |
|-------------|-------------------|
| Inactivity (was active) | Personal check-in email |
| Usage drop | Feature highlight email (new/underused features) |
| Failed payments | Payment method update reminder + grace period |
| Competitor mention | Value demonstration, roadmap preview |
| Price complaint | Annual discount offer (save 20%) |
| Missing features | Roadmap update, workaround guidance |

### Win-Back Campaign

For already-churned customers:
1. Wait 30 days after cancellation
2. Send personalized email highlighting new features since they left
3. Offer limited-time reactivation incentive
4. Track win-back conversion rate by churn reason

### Rules

- Act before churn happens, not after
- Base risk scores on behavior, not assumptions
- Suggest specific retention actions per user
- Track which retention strategies work
- Include revenue impact in every report
- Do not alert on every inactive user (set sensible thresholds)
- Do not assume all churn is preventable
- Do not recommend discounts as the first option
- Distinguish voluntary vs. involuntary churn
