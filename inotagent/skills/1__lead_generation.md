---
name: lead_generation
description: Build targeted prospect lists, enrich contacts, score leads by fit and intent, and identify buying triggers.
tags: [business, sales, leads, prospecting]
source: awesome-openclaw-agents/agents/business/lead-gen
---

## Lead Generation

> ~575 tokens

### ICP (Ideal Customer Profile) Definition

Before building any list, confirm targeting criteria:

| Criteria | Value |
|----------|-------|
| Stage | (Seed, Series A, Series B, etc.) |
| Model | (B2B SaaS, marketplace, services, etc.) |
| Size | (employee count range) |
| Geography | (countries/regions) |
| Industry | (verticals to include/exclude) |
| Decision maker titles | (CTO, VP Engineering, etc.) |

### Lead List Building Workflow

1. Define ICP criteria (refuse vague "get me leads" requests)
2. Research companies for firmographic and technographic data
3. Enrich contacts with verified emails, titles, LinkedIn profiles
4. Include data source and confidence level for each enriched field
5. Flag stale data (job titles older than 6 months need re-verification)

### Lead Scoring Model

| Factor | Weight | Score Range |
|--------|--------|-------------|
| Fit score (firmographic match) | 50% | 0-10 |
| Intent score (buying signals) | 50% | 0-10 |
| **Total** | | 0-20 |

Priority tiers:
- **P1 (15-20):** Immediate outreach
- **P2 (10-14):** Nurture sequence
- **P3 (0-9):** Monitor for trigger events

### Buying Trigger Signals

| Trigger | Signal Strength | Source |
|---------|----------------|--------|
| New CTO/VP hired | Strong | LinkedIn, press releases |
| Hiring surge | Strong | Job postings |
| Funding round | Strong | Crunchbase, news |
| Product launch | Medium | Product Hunt, blog |
| Office expansion | Medium | Local news |
| Tech stack change | Medium | Job postings, BuiltWith |

### TAM (Total Addressable Market) Estimation

1. Count total companies matching ICP criteria
2. Multiply by average deal size
3. Segment by tier (enterprise, mid-market, SMB)
4. Estimate market penetration rate

### Rules

- Always define ICP criteria before building any list
- Verify email patterns before including them
- Include data source and confidence level for every enriched field
- Never scrape personal emails -- business emails only
- Flag stale data (>6 months on job title)
- Respect GDPR and CAN-SPAM; note opt-in requirements by region
- Prioritize lead quality over quantity
