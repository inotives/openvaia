---
name: growth_strategy
description: Growth loop design, AARRR funnel optimization, viral mechanics, channel evaluation, and experiment framework
tags: [marketing, growth, acquisition, retention]
source: agency-agents/marketing/marketing-growth-hacker
---

## Growth Strategy

> ~1400 tokens

### AARRR Funnel Framework

| Stage | Metric | Target | Optimization Levers |
|-------|--------|--------|---------------------|
| **Acquisition** | New users/month | Channel-dependent | SEO, paid ads, content, partnerships, PR |
| **Activation** | % completing key action in first session | 60%+ in week 1 | Onboarding flow, time-to-value, first win |
| **Retention** | D7: 40%, D30: 20%, D90: 10% | Cohort-specific | Feature adoption, habit loops, notifications |
| **Revenue** | LTV:CAC >= 3:1 | CAC payback < 6 months | Pricing, upsell, expansion revenue |
| **Referral** | Viral coefficient (K-factor) | K > 1.0 for viral growth | Referral programs, sharing mechanics, incentives |

### Growth Loop Design

A growth loop is a closed system where output feeds back as input:

1. **Identify the loop**: User action -> creates value -> attracts new users -> repeat
2. **Common loop types**:
   - **Content loop**: Users create content -> indexed by search -> attracts new users
   - **Viral loop**: Users invite others -> invitees become users -> they invite more
   - **Paid loop**: Revenue -> reinvested in ads -> acquires users -> generates revenue
   - **Data loop**: More users -> better product (ML/network effects) -> attracts more users
3. **Measure cycle time**: How long from input to output? Shorter = faster growth
4. **Identify leaks**: Where do users drop out of the loop? Fix highest-impact leak first

### Channel Evaluation Framework (ICE Score)

For each potential growth channel, score 1-10:

- **Impact**: How many users could this channel reach?
- **Confidence**: How sure are we this will work? (data/evidence)
- **Ease**: How quickly/cheaply can we test this?

ICE Score = (Impact + Confidence + Ease) / 3. Prioritize highest scores.

### Experiment Framework

```
Experiment: [name]
Hypothesis: If we [change], then [metric] will [improve by X%] because [reasoning]
Primary Metric: [what we measure]
Secondary Metrics: [guardrail metrics to watch]
Sample Size: [required for statistical significance]
Duration: [minimum runtime]
Success Criteria: [specific threshold, e.g., +5% conversion with p < 0.05]

Results:
- Control: [baseline metric]
- Variant: [test metric]
- Lift: [% change]
- Confidence: [p-value / confidence interval]
- Decision: SHIP / ITERATE / KILL
- Learnings: [what we learned regardless of outcome]
```

Target velocity: 10+ experiments/month, 30% expected winner rate.

### Viral Mechanics Playbook

- **Inherent virality**: Product requires others (messaging, collaboration tools)
- **Incentivized referrals**: Both referrer and invitee get value (credits, features)
- **Social proof**: Public usage signals (badges, profiles, leaderboards)
- **Content sharing**: User-generated content shareable outside the product
- **Network effects**: Product gets better with more users (marketplaces, platforms)

K-factor = invites per user x conversion rate per invite. K > 1 = viral growth.

### Retention Strategies by Stage

**Week 1 (Activation)**
- Reduce time-to-value: get user to "aha moment" ASAP
- Progressive onboarding (don't overwhelm)
- Trigger-based emails/notifications for incomplete setup

**Month 1 (Engagement)**
- Feature discovery campaigns
- Usage milestones and celebrations
- Community/social connections within product

**Month 3+ (Habit)**
- Personalization based on usage patterns
- Advanced features for power users
- Loyalty/status programs

**At Risk (Win-back)**
- Re-engagement campaigns with new value proposition
- Special offers or feature unlocks
- Direct outreach for high-value users

### North Star Metric Selection

Choose one metric that captures core value delivery:
- Must correlate with long-term revenue
- Must reflect user getting value (not vanity)
- Must be actionable by the team
- Examples: weekly active users, messages sent, transactions completed, content published

### Key Benchmarks

- CAC payback period: < 6 months
- LTV:CAC ratio: >= 3:1
- Monthly organic growth: 20%+ MoM
- Activation rate: 60%+ in first week
- Experiment winner rate: ~30% of tests
