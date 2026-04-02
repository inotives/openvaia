---
name: technical_design_doc
description: Technical design document — architecture, components, data flow, API contracts, tradeoffs, edge cases
tags: [planning, design, architecture]
source: openspec/Fission-AI/OpenSpec
---
# Technical Design Document

Document the technical approach BEFORE coding. Covers: how to build it, component design, data flow, alternatives considered, and edge cases.

## When to Use

- After a requirement spec (`SPEC:`) is written
- For medium-to-large features with architectural decisions
- When multiple implementation approaches exist
- When the change affects APIs, data models, or system architecture

For small changes with obvious implementation, skip to writing a plan.

## Design Structure

### 1. Context
Background and current state. What exists today that this design builds on or changes.

### 2. Approach
High-level technical approach in 2-3 sentences. The "elevator pitch" for how you'll build it.

### 3. Goals / Non-Goals
**Goals:** What this design achieves.
**Non-Goals:** What is explicitly out of scope for this design (even if related).

### 4. Components

```
[Component A] — [responsibility]
    ↓
[Component B] — [responsibility]
    ↓
[Component C] — [responsibility]
```

For each component: what it does, how to use it, what it depends on.

### 5. Data Flow

Use ASCII diagrams for complex flows:
```
User → API Gateway → Auth Service → Database
                  ↓
              Cache (read-through)
```

### 6. API Contract (if applicable)

```
POST /api/endpoint
  Request:  { field: type }
  Response: { field: type }
  Errors:   400 (validation), 401 (auth), 500 (server)
```

### 7. Alternatives Considered

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| Option A | [pros] | [cons] | **Selected** / Rejected |
| Option B | [pros] | [cons] | Rejected — [reason] |

### 8. Edge Cases & Error Handling
- [Edge case 1] — how handled
- [Edge case 2] — how handled
- [Failure mode] — recovery strategy

### 9. Testing Strategy
- Unit tests for [what]
- Integration tests for [what]
- Manual testing for [what]

## Storage

Store the design as a research report with `DESIGN:` prefix and `design` tag:
```
research_store(
  title="DESIGN: [Feature Name]",
  body="[full design content]",
  tags=["design", "<domain-tags>"]
)
```

## Key Principles

- **Design for isolation** — each component should have one clear purpose and well-defined interfaces
- **Prefer smaller, focused components** — easier to reason about, test, and modify
- **Show alternatives** — demonstrates you considered options, not just picked the first idea
- **ASCII diagrams over prose** — a diagram is worth a thousand words for data flow
- **Edge cases are first-class** — if you haven't thought about failure modes, the design is incomplete

## Process

1. Read the approved spec (`research_search(tags=["spec"])`)
2. Write the design following the structure above
3. Store via `research_store` with `DESIGN:` prefix and `design` tag
4. Present to human for review
5. If approved → proceed to implementation plan (writing_plans skill)
