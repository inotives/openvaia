# ES-0013 — Spec-Driven Development Skills

## Status: DRAFT

## Objective

Extract structured development workflow skills from [OpenSpec](https://github.com/Fission-AI/OpenSpec) — a spec-driven development framework. These skills teach agents to organize work as: Proposal → Spec → Design → Tasks → Implementation → Verification, using RFC 2119 requirements and Given/When/Then scenarios.

## Why

Our agents can research, code, and operate tools — but they lack a structured methodology for **planning and specifying changes** before implementing them. Current planning is ad-hoc:

- `brainstorming` skill explores ideas but doesn't produce structured specs
- `writing_plans` skill creates task lists but not requirements or designs
- Agents jump to implementation without documenting what "done" looks like
- No verification against spec after implementation

OpenSpec provides a proven, agent-friendly framework for this gap.

## What We Already Have (Overlap Analysis)

| OpenSpec Skill | Our Existing Skill | Overlap | Action |
|----------------|-------------------|---------|--------|
| `propose` | `brainstorming` | Medium — brainstorming explores ideas, propose structures them | **Extract** — different output format |
| `explore` | None | None | **Extract** — unique investigation mode |
| `apply` | `subagent_driven_development` | High — both execute task lists | **Skip** — we have this |
| `verify` | `verification_before_completion` | Medium — both verify work | **Extract** — spec-specific verification adds value |
| `ff` (fast-forward) | `writing_plans` | High — both create all planning artifacts at once | **Skip** — we have this |
| `archive` | `finishing_dev_branch` | Medium — both handle completion | **Skip** — we have this |
| `onboard` | None | None | **Skip** — framework-specific |

## Skills to Extract (4 non-overlapping)

### 1. `spec_driven_proposal` — Structured Change Proposal

**Source:** OpenSpec `propose` workflow + `proposal.md` template

**What it teaches:**
- Structure a change request with: motivation, scope, impact, success criteria, rollback plan
- Define what's changing AND what's not changing (scope boundaries)
- Identify affected components and teams
- Risk assessment before implementation

**Template output:**
```markdown
# Proposal: [Change Name]

## Motivation
Why this change is needed. What problem it solves.

## Scope
### In Scope
- [What this change includes]
### Out of Scope
- [What this change explicitly excludes]

## Success Criteria
- [ ] [Measurable outcome 1]
- [ ] [Measurable outcome 2]

## Impact Assessment
- **Components affected:** [list]
- **Risk level:** [low/medium/high]
- **Rollback plan:** [how to undo if it fails]

## Open Questions
- [Unresolved decisions that need input]
```

**How agents use it:**
- Before starting any significant feature or change
- After brainstorming (brainstorming → proposal → spec → design → tasks)
- Creates a reviewable document for human approval

### 2. `requirement_specification` — RFC 2119 Requirements with Scenarios

**Source:** OpenSpec spec format + `spec.md` template + `spec.schema.ts`

**What it teaches:**
- Write behavioral requirements using RFC 2119 keywords (MUST, SHALL, SHOULD, MAY)
- Define testable scenarios using Given/When/Then
- Structure specs by domain/feature area
- Distinguish between must-have (MUST/SHALL) and nice-to-have (SHOULD/MAY)

**Template output:**
```markdown
# [Domain] Specification

## Purpose
What this spec covers and why it exists.

## Requirements

### Requirement: User Authentication
The system MUST authenticate users via email + password before granting access.

#### Scenario: Successful Login
- GIVEN a registered user with valid credentials
- WHEN they submit email and password
- THEN they receive an access token AND are redirected to dashboard

#### Scenario: Invalid Password
- GIVEN a registered user
- WHEN they submit an incorrect password
- THEN they receive a 401 error AND the attempt is logged

#### Scenario: Account Locked
- GIVEN a user with 5 failed login attempts
- WHEN they attempt to login again
- THEN the account is locked for 30 minutes AND user is notified
```

**How agents use it:**
- After a proposal is approved, write the spec
- Each requirement is independently testable
- Scenarios become the basis for test cases
- Spec becomes the "contract" — implementation verified against it

### 3. `technical_design_doc` — Architecture & Approach Documentation

**Source:** OpenSpec `design.md` template + design workflow

**What it teaches:**
- Document the technical approach before coding
- Cover: architecture, data flow, component design, API contracts
- Identify tradeoffs and alternatives considered
- Plan for error handling, edge cases, performance
- Include sequence diagrams (ASCII) for complex flows

**Template output:**
```markdown
# Technical Design: [Feature Name]

## Approach
High-level technical approach (2-3 sentences).

## Architecture
### Components
- [Component A] — [responsibility]
- [Component B] — [responsibility]

### Data Flow
```
User → API Gateway → Auth Service → Database
                  → Cache (read-through)
```

## API Contract
### POST /api/auth/login
- Request: `{ email: string, password: string }`
- Response: `{ token: string, expires_in: number }`
- Errors: 401 (invalid), 429 (rate limited), 423 (locked)

## Alternatives Considered
| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| JWT tokens | Stateless, scalable | Can't revoke | **Selected** |
| Session cookies | Easy revocation | Requires session store | Rejected |

## Edge Cases
- Concurrent login from multiple devices
- Token expiration during active session
- Database failover during auth

## Testing Strategy
- Unit tests for auth logic
- Integration tests for full login flow
- Load test for concurrent auth requests
```

**How agents use it:**
- After spec is written, create the design
- Design becomes the blueprint for implementation
- Reviewable by human before coding starts

### 4. `spec_verification` — Verify Implementation Against Spec

**Source:** OpenSpec `verify` workflow

**What it teaches:**
- After implementation, systematically verify every requirement in the spec
- Check each scenario's Given/When/Then against actual behavior
- Report: PASS, FAIL, PARTIAL, NOT TESTED
- Identify gaps between spec and implementation
- Generate verification report

**Template output:**
```markdown
# Verification Report: [Feature Name]

## Summary
- **Total requirements:** 5
- **Verified:** 4 (80%)
- **Passed:** 3
- **Failed:** 1
- **Not tested:** 1

## Results

### Requirement: User Authentication — PASS
- ✅ Scenario: Successful Login — verified via test_login_success
- ✅ Scenario: Invalid Password — verified via test_login_invalid
- ✅ Scenario: Account Locked — verified via test_account_lockout

### Requirement: Password Reset — FAIL
- ✅ Scenario: Request Reset — verified
- ❌ Scenario: Expired Token — token accepted after expiry (BUG)
- ⚠️ Scenario: Rate Limiting — not tested

## Action Items
1. Fix expired token validation (MUST)
2. Add rate limiting test (SHOULD)
```

**How agents use it:**
- After implementation is complete, run verification
- Cross-reference spec requirements against code/tests
- Generate evidence-based completion report
- Replaces vague "it works" with structured proof

## Complete Workflow Integration

These 4 skills form a pipeline that integrates with our existing skills:

```
brainstorming (existing)
    ↓ idea explored, approach chosen
spec_driven_proposal (new)
    ↓ proposal approved by human
requirement_specification (new)
    ↓ spec written with Given/When/Then
technical_design_doc (new)
    ↓ design reviewed
writing_plans (existing)
    ↓ tasks broken down
subagent_driven_development (existing)
    ↓ implementation complete
spec_verification (new)
    ↓ verified against spec
finishing_dev_branch (existing)
    ↓ merged / shipped
```

Not every change needs all steps. Agent decides based on complexity:
- **Small fix:** brainstorming → writing_plans → verification
- **Medium feature:** proposal → spec → writing_plans → verification
- **Large feature:** brainstorming → proposal → spec → design → writing_plans → verification

## Document Trail Before Implementation

With the full pipeline, these documents are created before any code is written:

```
1. Brainstorming Notes (existing — memory_store)
   └─ Exploration of the idea, approaches considered, recommendation

2. Proposal (NEW — spec_driven_proposal)
   └─ Motivation, scope, success criteria, impact, rollback plan, open questions

3. Requirement Spec (NEW — requirement_specification)
   └─ RFC 2119 requirements + Given/When/Then scenarios (the "contract")

4. Technical Design (NEW — technical_design_doc)
   └─ Architecture, components, data flow, API contracts, alternatives, edge cases

5. Implementation Plan (existing — writing_plans)
   └─ Bite-sized tasks with exact file paths, code blocks, test commands

--- after implementation ---

6. Verification Report (NEW — spec_verification)
   └─ Every requirement checked: PASS / FAIL / NOT TESTED
```

### Scaling by Complexity

Not every change needs all 5 documents. Agent decides based on complexity:

| Change Size | Documents Before Coding | Example |
|------------|------------------------|---------|
| **Quick fix** | Plan only | "Fix typo in API response" |
| **Small feature** | Plan + Verification | "Add pagination to task list" |
| **Medium feature** | Proposal + Spec + Plan + Verification | "Add email notifications" |
| **Large feature** | All 5 (brainstorm + proposal + spec + design + plan) + Verification | "Multi-agent trading system" |

### Document Storage

| Document | Storage | Tool Used |
|----------|---------|-----------|
| Brainstorming notes | Agent memory | `memory_store` |
| Proposal | Research report | `research_store` |
| Requirement spec | Research report | `research_store` |
| Technical design | Research report | `research_store` |
| Implementation plan | Task with subtasks | `task_create` |
| Verification report | Research report | `research_store` |

All discoverable via `research_search` and visible in the Admin UI Research tab + office panel.

## Implementation Steps

- [ ] Extract `spec_driven_proposal` skill from OpenSpec propose workflow + template
- [ ] Extract `requirement_specification` skill from OpenSpec spec format + schema
- [ ] Extract `technical_design_doc` skill from OpenSpec design template + workflow
- [ ] Extract `spec_verification` skill from OpenSpec verify workflow
- [ ] Import all 4 skills via `make import-skills`
- [ ] Test: ask agent to plan a feature using the full pipeline
- [ ] Update changelog

## Dependencies

- No code changes needed — these are pure skill files (markdown)
- No new tools — agents use existing tools (task_create, research_store, memory_store)
- No DB changes
- Source: [OpenSpec](https://github.com/Fission-AI/OpenSpec) by Fission AI (MIT License)

## Estimated Effort

1 day — skill extraction + testing. No code changes.

## References

- [OpenSpec](https://github.com/Fission-AI/OpenSpec) — Spec-driven development framework
- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) — Key words for requirement levels
- Existing skills: `brainstorming`, `writing_plans`, `verification_before_completion`, `subagent_driven_development`, `finishing_dev_branch`
