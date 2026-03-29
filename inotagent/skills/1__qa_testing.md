---
name: qa_testing
description: Systematic QA — test, classify bugs by severity, atomic fixes with before/after evidence
tags: [testing, qa, quality]
source: gstack/garrytan/gstack
---
# QA Testing

Systematic QA methodology: interact with every element, classify bugs by severity, fix atomically with evidence.

## When to Use

- After implementing a feature or fix
- Before shipping to production
- When testing a new UI flow end-to-end

## Test Tiers

| Tier | Scope | When |
|------|-------|------|
| **Quick** | Critical + High severity only | Before every merge |
| **Standard** | + Medium severity | Before release |
| **Exhaustive** | + Low/cosmetic | Major releases, new features |

## The Process

### 1. Setup
- Identify the URL/entry point to test
- Ensure clean working tree (no uncommitted changes)
- Detect or set up test framework

### 2. Interactive Testing
- **Click everything** — every button, link, tab, dropdown
- **Fill every form** — valid data, empty, edge cases (long strings, special chars)
- **Test navigation** — back/forward, direct URL, deep links
- **Check states** — loading, empty, error, success, partial data
- **Responsive** — mobile, tablet, desktop breakpoints

### 3. Bug Classification

| Severity | Definition | Examples |
|----------|-----------|---------|
| **Critical** | App crashes, data loss, security hole | Unhandled exception, missing auth check |
| **High** | Feature broken, blocks user workflow | Button does nothing, form won't submit |
| **Medium** | Works but incorrect/confusing | Wrong data displayed, misleading label |
| **Low** | Cosmetic, minor inconvenience | Misaligned text, wrong color shade |

**Bug Categories:** Visual/UI, Functional, UX, Content, Performance, Console/Errors, Accessibility

### 4. Atomic Fixes
Each bug gets its own fix:
1. Document the bug (what, where, severity)
2. Fix the root cause (not the symptom)
3. Verify the fix (re-test the specific flow)
4. Commit with descriptive message: `fix: [what was broken]`

Never bundle multiple bug fixes in one commit.

### 5. Re-Verification
After all fixes: re-test broken flows, run test suite, check no new issues.

## Per-Page Checklist

- [ ] Page loads without errors
- [ ] All interactive elements respond
- [ ] Forms validate and submit correctly
- [ ] Error states display meaningful messages
- [ ] Loading states show feedback
- [ ] Empty states handled gracefully
- [ ] Data displays correctly
- [ ] Navigation works
- [ ] Console is clean

## Output

```
## QA Report
**Tested:** [scope]  **Tier:** [Quick/Standard/Exhaustive]

| # | Severity | Category | Description | Status |
|---|----------|----------|-------------|--------|
| 1 | High | Functional | [description] | Fixed |

**Verdict:** [PASS / PASS WITH NOTES / FAIL]
```
