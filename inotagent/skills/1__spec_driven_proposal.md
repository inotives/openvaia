---
name: spec_driven_proposal
description: Structured change proposal — motivation, scope, success criteria, impact assessment, rollback plan
tags: [planning, proposal, workflow]
source: openspec/Fission-AI/OpenSpec
---
# Spec-Driven Proposal

Before implementing any significant change, create a structured proposal that answers: Why, What, and What Could Go Wrong.

## When to Use

- New features that affect multiple components
- Changes to APIs, data models, or user-facing behavior
- Anything that takes more than a few hours to implement
- When human approval is needed before coding

For quick fixes or trivial changes, skip directly to a plan.

## Proposal Structure

### 1. Motivation (Why)
- What problem does this solve?
- Why now? What triggered this?
- What happens if we don't do it?

### 2. What Changes
Be specific about new capabilities, modifications, or removals.
- **New:** What doesn't exist today that will exist after
- **Modified:** What existing behavior changes
- **Removed:** What goes away

### 3. Scope Boundaries
**In Scope:**
- [Specific deliverables]

**Out of Scope:**
- [Things that might seem related but are excluded]

### 4. Success Criteria
Measurable outcomes — how do we know it worked?
- [ ] [Criterion 1 — observable, testable]
- [ ] [Criterion 2 — observable, testable]

### 5. Impact Assessment
- **Components affected:** [list files, services, APIs]
- **Risk level:** low / medium / high
- **Dependencies:** [external systems, other teams]
- **Migration needed:** yes / no

### 6. Rollback Plan
How to undo this change if it fails:
- [Step-by-step rollback procedure]

### 7. Open Questions
Unresolved decisions that need human input:
- [Question 1]

## Storage

Store the proposal as a research report with `PROP:` prefix and `proposal` tag:
```
research_store(
  title="PROP: [Change Name]",
  body="[full proposal content]",
  tags=["proposal", "<domain-tags>"]
)
```

## Process

1. Write the proposal using the structure above
2. Store via `research_store` with `PROP:` prefix and `proposal` tag
3. Present to human for review
4. If approved → proceed to requirement specification (`SPEC:`)
5. If rejected → revise and re-present

## Key Principles

- **Be specific, not vague** — "improve performance" is not a scope item; "reduce API latency from 500ms to 200ms" is
- **Scope boundaries prevent scope creep** — listing what's OUT of scope is as important as what's IN
- **Success criteria must be testable** — if you can't verify it, you can't claim it's done
- **Rollback plan is mandatory** — every change must be reversible
- **Open questions surface early** — discover unknowns now, not mid-implementation
