---
name: competitor_pricing_analysis
description: Monitor competitor pricing changes, compare feature-by-feature value, and recommend positioning strategies.
tags: [business, pricing, competitive-intelligence, strategy]
source: awesome-openclaw-agents/agents/business/competitor-pricing
---

## Competitor Pricing Analysis

> ~497 tokens

### Pricing Comparison Framework

Compare on multiple dimensions, not just sticker price:

| Dimension | What to Compare |
|-----------|----------------|
| Per-user cost | Price / included users |
| Per-feature cost | Price / number of features |
| Plan tiers | Starter, Pro, Enterprise feature gates |
| Usage limits | API calls, storage, seats included |
| Contract terms | Monthly vs. annual, lock-in periods |
| Hidden costs | Overage fees, add-on pricing |

### Competitor Pricing Comparison Format

```
Pricing Comparison -- <tier> equivalent

| Competitor | Price/mo | Users | Features | Per-User Cost |
|------------|----------|-------|----------|---------------|

Gap Analysis:
- <competitor> offers features you lack: <list>
- Your advantage: <differentiator>

Recommendation: <positioning strategy>
```

### Pricing Change Alert Format

```
Pricing Change Detected -- <competitor>

Change: <old price> -> <new price> (<percent change>)
Tier affected: <which plan>
New tiers added: <if any>

Analysis:
- Direction: Moving upmarket / downmarket / expanding range
- Your position: Now <percent> cheaper/more expensive
- Opportunity: <recommendation>
- Risk: <what to watch for>
```

### Positioning Strategies

| Strategy | When to Use |
|----------|-------------|
| **Penetration** | Undercut competitors to gain market share |
| **Premium** | Higher price justified by superior features/support |
| **Value-based** | Price based on customer value delivered, not competitor reference |
| **Freemium** | Free tier to capture market, monetize on upgrades |

### Monitoring Cadence

- Scan competitor pricing pages weekly
- Track historical pricing changes over time
- Alert on pricing changes within hours
- Quarterly competitive pricing report

### Rules

- Compare pricing on a per-feature and per-user basis, not just sticker price
- Track historical pricing trends and change frequency
- Include both the opportunity and the risk in any pricing change analysis
- Update competitor data at least weekly
