---
name: vendor_evaluation
description: Score and rank vendors across quality, cost, delivery, and responsiveness with weighted comparative analysis.
tags: [supply-chain, procurement, vendor, evaluation]
source: awesome-openclaw-agents/agents/supply-chain/vendor-evaluator
---

## Vendor Evaluation

> ~673 tokens

### Scoring Methodology

Weighted average across standardized criteria:

| Criteria | Default Weight | Score Range |
|----------|---------------|-------------|
| Quality | 30% | 0-100 |
| Price/Cost | 25% | 0-100 |
| On-Time Delivery | 25% | 0-100 |
| Responsiveness | 20% | 0-100 |

Adjust weights based on organizational priorities (document the rationale).

### Vendor Comparison Format

```
Vendor Comparison -- <category> <year>

Scoring Methodology:
<weights and their justification>

| Criteria | Vendor A | Vendor B | Vendor C |
|----------|----------|----------|----------|
| Quality (30%) | /100 | /100 | /100 |
| Price (25%) | /100 | /100 | /100 |
| On-Time Delivery (25%) | /100 | /100 | /100 |
| Responsiveness (20%) | /100 | /100 | /100 |
| Weighted Score | | | |

Key Findings:
- <vendor>: <standout strength and weakness>

Recommendation:
- Primary: <vendor> for <use case>
- Secondary: <vendor> for <use case>
- Caution: <vendor> -- <concern to resolve before expanding>
```

### Risk Assessment Checklist

- [ ] Performance trend (improving or declining over last 4 quarters)
- [ ] Financial stability indicators
- [ ] Compliance with contractual SLAs
- [ ] Regulatory compliance status
- [ ] Single-source dependency risk
- [ ] Capacity to handle volume increases

### Discount/Volume Offer Analysis

When a vendor offers a price reduction for volume increase:

```
Discount Analysis -- <vendor>

Offer: <percent>% price reduction for <percent>% volume increase

| Factor | Current | With Discount |
|--------|---------|---------------|
| Unit cost | $ | $ |
| Annual spend | $ | $ |
| Net savings | -- | $/year |

Risks:
1. <capacity/delivery risk at higher volume>
2. <quality risk at higher volume>
3. <supplier concentration risk>

Recommendation: <accept/counter-offer/decline with reasoning>
```

### Vendor Criticality Tiers

| Tier | Criteria | Review Frequency |
|------|----------|-----------------|
| Strategic | High spend, hard to replace, direct revenue impact | Monthly |
| Important | Moderate spend, alternatives exist | Quarterly |
| Routine | Low spend, easily replaceable | Annually |

### Rules

- Base all scores on documented evidence and measurable metrics
- Clearly state the weighting methodology used
- Highlight both strengths and weaknesses for each vendor
- Recommend review frequency based on vendor criticality tier
- Do not allow subjective preferences to override data-driven scoring
- Do not ignore small vendors that may offer competitive advantages
- Never present vendor scores without explaining the methodology
- Never recommend sole-sourcing without flagging supply chain risk
