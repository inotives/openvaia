---
name: product_ops
description: Feature request triage, ICE scoring, release notes generation, and changelog management
tags: [product, release, feature-request, changelog]
source: awesome-openclaw-agents/saas/release-notes, awesome-openclaw-agents/saas/feature-request
---

## Product Operations

> ~653 tokens

### Feature Request Triage

When a feature request comes in:
1. **Log it** — title, description, requester, requester tier/plan
2. **Deduplicate** — check for similar existing requests, combine if overlapping
3. **Categorize** — assign a product area tag
4. **Score** — apply ICE framework
5. **Rank** — update backlog position

### ICE Scoring Framework
- **Impact** (1-10): How much will this move the target metric?
- **Confidence** (1-10): How sure are we about the impact estimate?
- **Ease** (1-10): How easy is this to implement? (10=trivial, 1=massive)
- **Score** = Impact x Confidence x Ease

| Score Range | Action |
|-------------|--------|
| 500+ | Prioritize for next sprint |
| 300-499 | Schedule for next quarter |
| 100-299 | Backlog — revisit monthly |
| <100 | Defer or decline with explanation |

### Feature Request Report Template
```
Top N by ICE Score:
| Rank | Feature | ICE | Requests | Revenue at Risk |
|------|---------|-----|----------|-----------------|
| 1 | [name] | [score] | [count] | [MRR] |

Recommendation: Ship [#X] and [#Y] — highest ROI, lowest effort.
```

### Release Notes

**Categorize changes:**
- **New** — wholly new capabilities
- **Improved** — enhancements to existing features
- **Fixed** — bug fixes
- **Breaking** — changes requiring user action (always flag prominently)

**Writing rules:**
- Lead with user benefit, not technical implementation
- One sentence per change, active voice
- Breaking changes include migration instructions
- Version number + date in header

**Release Notes Template:**
```
## vX.Y.Z — [Date]

### New
- [Feature] — [user benefit in one sentence]

### Improved
- [Feature] — [what changed and why it matters]

### Fixed
- [Bug] — [what was broken and how it affects users]

### Breaking
- [Change] — [what users need to do]. See [migration guide].
```

**Audience-specific summaries:**
- **Users:** focus on benefits and how-to
- **Developers:** include API changes, deprecations, SDK updates
- **Stakeholders:** highlight metrics impact and strategic alignment

### Email Announcement Template (Major Releases)
```
Subject: "New: [Feature] — [benefit in 5 words]"
Body:
- One sentence: what it does
- One sentence: why it matters
- Single CTA button
- Sign-off
```
