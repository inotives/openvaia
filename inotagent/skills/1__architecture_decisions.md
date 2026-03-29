---
name: architecture_decisions
description: ADR templates, DDD concepts, trade-off analysis frameworks, and pattern selection guides
tags: [architecture, adr, ddd, trade-offs, patterns]
source: agency-agents/engineering/engineering-software-architect.md
---

## Architecture Decision Record (ADR) Template

> ~979 tokens

Use this template when making significant technical decisions.

```
# ADR-NNN: [Decision Title]

## Status
Proposed | Accepted | Deprecated | Superseded by ADR-XXX

## Context
What problem or situation is driving this decision?
What constraints exist (team size, timeline, budget, existing systems)?

## Options Considered
### Option A: [Name]
- Pros: ...
- Cons: ...
- Risk: ...

### Option B: [Name]
- Pros: ...
- Cons: ...
- Risk: ...

## Decision
Which option was chosen and why.

## Consequences
- What becomes easier?
- What becomes harder?
- What needs follow-up work?
```

## Domain-Driven Design (DDD) Checklist

### Bounded Context Discovery
1. List the major business capabilities (e.g., billing, inventory, auth)
2. For each capability, identify:
   - Core domain events (things that happened: "OrderPlaced", "PaymentReceived")
   - Commands (actions requested: "PlaceOrder", "ProcessPayment")
   - Aggregates (consistency boundaries: Order, Payment)
   - Invariants (rules that must always hold: "Order total must match line items")
3. Draw context boundaries where the same word means different things (e.g., "User" in Auth vs "Customer" in Billing)

### Context Mapping Patterns
| Pattern | When to Use |
|---------|------------|
| Shared Kernel | Two teams co-own a small model (high trust required) |
| Customer-Supplier | Upstream serves downstream; downstream can negotiate |
| Conformist | Downstream accepts upstream model as-is (no leverage) |
| Anti-Corruption Layer | Translate between contexts to prevent model pollution |
| Open Host / Published Language | Public API with documented schema |

## Trade-off Analysis Framework

When evaluating architectural options, score each on these axes:

| Axis | Question |
|------|----------|
| **Complexity** | How much does this add to the system's cognitive load? |
| **Coupling** | How many things break if this changes? |
| **Reversibility** | How hard is it to undo this decision later? |
| **Team fit** | Can the current team build and maintain this? |
| **Time to value** | How long until this delivers business value? |
| **Operational cost** | What's the ongoing maintenance burden? |

**Decision rule**: Prefer reversible decisions. When two options are close, pick the simpler one. Name what you're giving up, not just what you're gaining.

## Architecture Pattern Selection Guide

### When to Stay Monolith
- Team < 8 engineers
- Domain boundaries unclear
- Shared database transactions needed
- Time-to-market is the priority

### When to Extract a Service
- One domain has different scaling needs
- One team needs independent deployment
- A bounded context has a clear, stable API surface
- You can accept eventual consistency at the boundary

### When to Go Event-Driven
- Workflows span multiple services
- You need audit trails / event sourcing
- Producers shouldn't know about consumers
- Throughput matters more than latency

### When to Use CQRS
- Read and write models diverge significantly
- Complex query patterns (aggregations, projections)
- Read:write ratio > 10:1
- Different scaling needs for reads vs writes

## Quality Attribute Checklist

Before finalizing any architecture, verify:

- [ ] **Scalability**: Can each component scale independently? Are services stateless?
- [ ] **Reliability**: What happens when service X is down? Is there a fallback?
- [ ] **Maintainability**: Can a new team member understand the boundaries in a day?
- [ ] **Observability**: Can you trace a request across all boundaries? What metrics matter?
- [ ] **Evolvability**: Can you replace a component without rewriting neighbors?
- [ ] **Security**: Is the blast radius of a compromise contained to one context?

## Anti-Patterns to Flag

- **Distributed monolith**: Microservices that must deploy together
- **Shared database**: Multiple services writing to the same tables
- **Architecture astronautics**: Abstractions without proven need
- **Resume-driven development**: Picking tech for novelty, not fit
- **Big bang migration**: Rewriting everything at once instead of strangling incrementally
