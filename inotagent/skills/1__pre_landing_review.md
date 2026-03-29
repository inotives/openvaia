---
name: pre_landing_review
description: Two-pass code review — scope drift detection, SQL safety, LLM boundaries, test coverage tracing
tags: [review, quality, development]
source: gstack/garrytan/gstack
---
# Pre-Landing Code Review

Structured two-pass review before merging code. Catches scope drift, critical safety issues, and design problems.

## When to Use

- Before merging any PR or feature branch
- Before deploying code to production
- When reviewing someone else's (or your own) implementation

## The Process

### Pass 1: Scope & Plan Compliance

1. **Scope Drift Detection** — Did they build what was requested? Compare diff against the original plan/spec. Flag additions not in scope.
2. **Plan Completion Audit** — If a plan file exists, verify every task is implemented. Missing tasks = not ready to merge.
3. **Enum/Value Completeness** — Read files outside the diff to verify new enum values, config keys, or API fields are used everywhere they should be.

### Pass 2: Critical + Informational Review

**CRITICAL issues (must fix before merge):**

| Category | What to check |
|----------|--------------|
| SQL Safety | Raw string interpolation, missing parameterization, injection vectors |
| Race Conditions | Shared state without locking, concurrent writes, TOCTOU bugs |
| LLM Trust Boundaries | User input passed to LLM without sanitization, LLM output used in SQL/shell without validation |
| Auth/AuthZ | Missing permission checks, privilege escalation paths |
| Data Loss | Destructive operations without confirmation, missing backups/transactions |
| Error Handling | Swallowed errors, missing try/catch on I/O operations |

**INFORMATIONAL issues (improve but don't block):**

| Category | What to check |
|----------|--------------|
| Dead Code | Unused imports, unreachable branches, commented-out code |
| Magic Numbers | Hardcoded values that should be constants |
| Naming | Unclear variable/function names, inconsistent conventions |
| Performance | N+1 queries, unnecessary re-renders, large bundle imports |
| Duplication | Copy-pasted code that should be extracted |

### Test Coverage Trace

For every code path changed:
- Is there a test that exercises this path?
- Does the test verify the expected behavior (not just that it doesn't crash)?
- Are edge cases covered (empty input, null, boundary values)?

### Design Review (if frontend changes)

- Does the UI match the spec/mockup?
- Are responsive breakpoints handled?
- Is the component accessible (keyboard nav, screen readers)?

## Output Format

```
## Review Summary

**Scope:** [matches plan / scope drift detected]
**Plan completion:** [X/Y tasks complete]

### Critical (must fix)
1. [file:line] — [issue description]

### Informational (suggestions)
1. [file:line] — [suggestion]

### Test Coverage
- [path] — covered / missing

**Verdict:** [APPROVE / REQUEST CHANGES]
```

## Fix-First Flow

When you find an issue:
1. **Can auto-fix safely?** → Fix it, note in review
2. **Need author input?** → Ask specific question with context
3. **Architecture concern?** → Flag for discussion, don't block on opinion
