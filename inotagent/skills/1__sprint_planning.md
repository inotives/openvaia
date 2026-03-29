---
name: sprint_planning
description: Agile sprint planning — user stories, estimation, velocity tracking, backlog prioritization
tags: [agile, scrum, planning, project-management]
source: awesome-openclaw-agents/saas/product-scrum
---

## Sprint Planning

> ~721 tokens

### User Story Format
```
As a [user type], I want [goal] so that [benefit].

Acceptance Criteria:
Given [context]
When [action]
Then [expected result]
And [additional conditions]
```

Every story must have acceptance criteria. No exceptions.

### Story Point Estimation
- Use story points (complexity), not hours (time)
- Stories larger than 8 points must be broken down before entering a sprint
- Estimation methods: planning poker, t-shirt sizing (XS=1, S=2, M=3, L=5, XL=8)

### Sprint Capacity
- Never exceed 15% carryover from previous sprint — address root cause if recurring
- Sprint scope locks after planning — changes go to next sprint backlog
- Recommended: 80% planned work, 20% buffer for unplanned/tech debt

### Backlog Prioritization Frameworks

**RICE Score:**
- Reach: how many users affected (per quarter)
- Impact: how much it moves the metric (0.25=minimal, 0.5=low, 1=medium, 2=high, 3=massive)
- Confidence: how sure you are (100%=high, 80%=medium, 50%=low)
- Effort: person-months
- Score = (Reach x Impact x Confidence) / Effort

**MoSCoW:**
- Must have: non-negotiable for this release
- Should have: important but not critical
- Could have: nice to have if time allows
- Won't have: explicitly deferred

**Weighted Shortest Job First (WSJF):**
- Score = Cost of Delay / Job Duration
- Cost of Delay = User Value + Time Criticality + Risk Reduction

### Velocity Analysis Checklist
When velocity drops, investigate:

| Cause | Signal | How to Check |
|-------|--------|--------------|
| Unplanned work | Bug fixes mid-sprint | Track interruption hours |
| Story inflation | 3-point stories taking 5+ days | Compare estimates vs actuals |
| Capacity change | PTO, context-switching, onboarding | Compare available vs planned capacity |
| Technical debt | Slow builds, flaky tests | Measure CI time, test failure rate |
| Scope creep | Requirements growing after planning | Count AC changes post-sprint-start |

### Sprint Retrospective
Action items from retros must be:
- **Specific** — not "improve communication" but "post daily updates in #standup by 10am"
- **Assigned** — one owner per action item
- **Time-bound** — deadline within the next sprint

### Epic Breakdown Template
```
Epic: [Name]
Goal: [One sentence — what users can do when this ships]

| ID | Story | Points | Priority |
|----|-------|--------|----------|
| E-01 | [story] | [pts] | P0/P1/P2 |

Sprint Recommendation:
| Sprint | Stories | Points | Focus |
|--------|---------|--------|-------|
| Sprint N | [IDs] | [pts] | [theme] |
```
