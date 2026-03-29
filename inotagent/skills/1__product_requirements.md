---
name: product_requirements
description: PRD template, opportunity assessment framework, roadmap prioritization, and GTM planning
tags: [product, prd, roadmap, prioritization, gtm]
source: agency-agents/product/product-manager
---

## Product Requirements & Planning

> ~1450 tokens

### PRD Template

```
# PRD: [Feature / Initiative Name]
Status: Draft | In Review | Approved | In Development | Shipped
Stakeholders: [Eng Lead, Design Lead, Marketing, Legal if needed]

## 1. Problem Statement
- What specific user pain or business opportunity?
- Who experiences it, how often, cost of not solving?
- Evidence: user research (n=X), behavioral data, support signal, competitive signal

## 2. Goals & Success Metrics
| Goal | Metric | Baseline | Target | Measurement Window |

## 3. Non-Goals
- Explicitly state what this iteration will NOT address and why

## 4. User Personas & Stories
- Primary persona with context
- Stories: As a [persona], I want [action] so that [outcome]
- Acceptance criteria: Given [context], when [action], then [result]
- Include edge cases and performance requirements

## 5. Solution Overview
- Narrative description (2-4 paragraphs)
- Key design decisions: chose [A] over [B] because [reason], trade-off: [X]

## 6. Technical Considerations
- Dependencies: [system] needed for [reason], owner, timeline risk
- Risk table: Risk | Likelihood | Impact | Mitigation
- Open questions with owners and deadlines

## 7. Launch Plan
| Phase | Date | Audience | Success Gate |
- Internal alpha -> Closed beta -> GA rollout (phased %)
- Rollback criteria: if [metric] drops below [threshold], revert
```

### Opportunity Assessment (RICE)

When evaluating a new opportunity:
1. **Why now?** — market signal, user shift, or competitive pressure; cost of waiting 6 months
2. **User evidence** — interviews (n=X with quotes), behavioral data, support signal (tickets/month)
3. **Business case** — revenue impact, cost impact, strategic fit to OKRs, market sizing (TAM/SAM)
4. **RICE score** — Reach (users/quarter) x Impact (0.25-3) x Confidence (%) / Effort (person-months)
5. **Options considered** — build full | MVP | buy/integrate | defer — with pros, cons, effort
6. **Recommendation** — build / explore / defer / kill with rationale and next step if approved

### Roadmap Prioritization (Now / Next / Later)

- **North star metric**: single metric capturing user value + business health, with current and target
- **Now (this quarter)**: committed work with initiative, user problem, success metric, owner, status, ETA
- **Next (1-2 quarters)**: directionally committed with hypothesis, expected outcome, confidence, blockers
- **Later (3-6 months)**: strategic bets with hypothesis and signal needed to advance
- **Not building**: rejected requests with source, reason, and revisit condition

### Product Lifecycle Phases

1. **Discovery** — 5-10 problem interviews, analytics friction audit, support ticket mining, journey mapping, evidence-backed problem statement
2. **Framing** — opportunity assessment, leadership alignment, engineering t-shirt sizing, RICE scoring, build/defer/kill recommendation
3. **Definition** — collaborative PRD, PRFAQ exercise, design kickoff with problem brief, dependency tracking, pre-mortem, scope lock with sign-off
4. **Delivery** — prioritized backlog with acceptance criteria, sprint ceremonies, 24h blocker resolution, weekly async status updates
5. **Launch** — GTM coordination, rollout strategy (feature flags/phased/AB), CS training before GA, rollback runbook, daily metrics for 2 weeks
6. **Measurement** — 30/60/90 day metric review, launch retrospective, post-launch interviews, feed insights back to discovery

### GTM Brief Checklist

- Launch tier (1=Major, 2=Standard, 3=Silent)
- Target audience segments with size, motivation, and channel to reach
- Value proposition one-liner: [Feature] helps [persona] [outcome] without [pain]
- Messaging matrix by audience: their language | our message | proof point
- Launch checklist: feature flag, monitoring, rollback runbook, in-app copy, release notes, help center, blog, email, sales deck, CS training
- Success criteria: error rate (day 1), activation (7d), retention (30d), support delta (60d), NPS (90d)
