---
name: task_breakdown
description: Spec-to-tasks breakdown, scoping, estimation, task sizing, dependency ordering, and acceptance criteria
tags: [task-management, planning, estimation, specs]
source: agency-agents/project-management/project-manager-senior
---

## Spec-to-Tasks Breakdown

> ~1051 tokens

### Breakdown Process

1. **Read the spec literally** — quote exact requirements, do not invent features
2. **Identify deliverables** — list every concrete output the spec demands
3. **Group by functional area** — structure tasks by feature/component
4. **Order by dependencies** — what must exist before the next thing can start
5. **Size each task** — target 30-60 minutes of implementation work per task
6. **Write acceptance criteria** — testable conditions for "done"
7. **Add technical notes** — files to create/edit, libraries needed, constraints

### Scoping Rules

- [ ] Only include what the spec explicitly requires
- [ ] Do not add "nice to have" or "premium" features
- [ ] Basic implementation is acceptable for v1
- [ ] Flag spec gaps as questions, do not fill them with assumptions
- [ ] Most specs are simpler than they first appear
- [ ] Plan for 2-3 revision cycles after initial implementation

### Task Sizing Guide

| Size | Duration | Description |
|------|----------|-------------|
| XS | <15 min | Config change, copy update, single-line fix |
| S | 15-30 min | Single function, simple component, basic test |
| M | 30-60 min | Feature slice, API endpoint, integration point |
| L | 1-2 hrs | Multi-file feature, complex logic, full test suite |
| XL | >2 hrs | **Split this into smaller tasks** |

**Rule**: If a task feels like L or XL, break it down further. Developers should be able to start and finish a task in one focused session.

### Dependency Ordering

1. **Foundation first** — data models, database schemas, base layouts
2. **Core logic second** — business rules, API endpoints, primary flows
3. **Integration third** — connecting components, external services
4. **Polish last** — styling, animations, edge cases, error handling

### Task Template

```
### [ ] Task N: [Short descriptive title]
**Description**: [What to build — specific, actionable]
**Acceptance Criteria**:
- [ ] [Testable condition 1]
- [ ] [Testable condition 2]
- [ ] [Testable condition 3]
**Files**: [files to create or modify]
**Dependencies**: [task IDs that must complete first]
**Size**: [XS/S/M/L]
**Reference**: [section of spec this implements]
```

### Estimation Checklist

- [ ] Break into tasks before estimating (never estimate the whole)
- [ ] Estimate implementation time, not calendar time
- [ ] Add time for: testing, code review, integration
- [ ] Account for unknowns — unfamiliar tech adds 50-100% overhead
- [ ] Compare against similar past tasks if available
- [ ] Sum task estimates + add 20% contingency = total estimate

### Acceptance Criteria Writing Guide

Good acceptance criteria are:
- **Testable** — can verify pass/fail unambiguously
- **Specific** — reference exact behavior, not vague outcomes
- **Independent** — each criterion stands alone
- **Complete** — cover the happy path + key error cases

Examples:
```
BAD:  "Form works properly"
GOOD: "Submitting form with valid name+email+message shows success message"
GOOD: "Submitting form with empty email shows validation error on email field"
GOOD: "Form submission creates record in database with all fields populated"
```

### Task List Document Template

```
# [Project Name] — Development Tasks

## Spec Summary
- Requirements: [quoted from spec]
- Stack: [exact tech requirements]
- Timeline: [from spec or estimated]

## Tasks

### Phase 1: Foundation
[Tasks for base setup, schemas, layouts]

### Phase 2: Core Features
[Tasks for primary functionality]

### Phase 3: Integration
[Tasks for connecting components]

### Phase 4: Polish
[Tasks for styling, edge cases, error handling]

## Quality Checklist
- [ ] All tasks have acceptance criteria
- [ ] No task exceeds 2 hours
- [ ] Dependencies are ordered correctly
- [ ] No features added beyond spec
- [ ] Technical requirements are complete
```

### Common Pitfalls

- **Scope creep**: Adding features not in the spec — always quote the source
- **Vague tasks**: "Implement backend" — break into specific endpoints/functions
- **Missing dependencies**: Task requires something that no prior task creates
- **Gold-plating**: Over-engineering v1 — basic working implementation first
- **Forgotten testing**: Every feature task should include its test criteria
