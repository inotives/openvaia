---
name: saas_analytics
description: Usage analytics, cohort analysis, funnel optimization, and user activation workflows
tags: [analytics, saas, onboarding, activation, cohort]
source: awesome-openclaw-agents/saas/usage-analytics, awesome-openclaw-agents/saas/onboarding-flow
---

## SaaS Analytics

> ~756 tokens

### Feature Adoption Analysis
Track per feature:
- **Adoption rate** — % of active users who used the feature (30-day window)
- **Frequency** — average uses per user per week
- **Retention correlation** — do users of this feature churn less?

**Underused feature checklist:**
1. Is it discoverable? (can users find it)
2. Is it useful? (does it solve a real problem)
3. Is it usable? (can users figure it out without help)
4. If high retention correlation but low adoption — invest in discovery/onboarding

### Cohort Analysis Template
```
[Month] Signup Cohort ([N] users):
| Period | Retention | vs Previous Cohort |
|--------|-----------|-------------------|
| Week 1 | [%] | [+/- pp] |
| Week 2 | [%] | [+/- pp] |
| Week 4 | [%] | [+/- pp] |
| Week 8 | [%] | [+/- pp] |

Drop-off correlates with: [event/change that happened on date X]
Recommendation: [specific action]
```

### Engagement Scoring
Define engagement score per user:
- Login frequency (daily=3, weekly=2, monthly=1, inactive=0)
- Core actions per session (above median=2, below=1, none=0)
- Feature breadth (3+ features=2, 1-2=1, core only=0)
- Score range: 0-7 (0-2=at risk, 3-4=moderate, 5-7=power user)

### Onboarding Funnel Optimization

**Define the aha moment:**
- What single action delivers first value to the user?
- Measure: time from signup to aha moment (target: under 5 minutes)

**Standard funnel stages:**
```
Signup (100%) > Setup ([%]) > First Action ([%]) > Core Value ([%]) > Repeat ([%])
```

**When activation is low, work backward from the biggest drop:**
1. Identify the step with largest % drop
2. Remove friction at that step (skip optional setup, prefill data, show guided demo)
3. Measure lift over 2-4 weeks

**Onboarding principles:**
- Skip anything that can be done later (profile setup, preferences)
- Get users to the core value action as fast as possible
- Use sample/demo data so users see value before investing effort
- Progressive disclosure — show advanced features after basics are mastered

### Onboarding Email Sequence
| Email | Timing | Purpose | CTA |
|-------|--------|---------|-----|
| Welcome | Immediate | One action that delivers value | Single button to core feature |
| Quick tip | +24h | Show most-used feature | Link with demo/GIF |
| Need help? | +72h | Offer human help | Book a call or link to docs |
| Success story | +7d | Social proof + advanced feature | Feature highlight |

Unsubscribe from sequence on any conversion event.

### Metric Comparison Rule
Always compare metrics against the previous period:
- Day-over-day for operational metrics
- Week-over-week for growth metrics
- Month-over-month for strategic metrics
- Include absolute numbers and percentage change
