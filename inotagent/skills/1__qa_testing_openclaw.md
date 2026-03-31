---
name: qa_testing_openclaw
description: Design test plans, write test cases with edge/negative scenarios, and draft structured bug reports.
tags: [development, testing, qa, quality]
source: awesome-openclaw-agents/agents/development/qa-tester
---

## QA Testing

> ~667 tokens

### Test Plan Structure

1. Define scope (feature, API, user flow)
2. Specify environment (browsers, devices, OS)
3. Categorize test cases: happy path, edge case, negative, destructive
4. Include preconditions and test data requirements for every test case
5. Define pass/fail criteria

### Test Case Design Techniques

- **Equivalence partitioning:** Divide inputs into groups that should behave the same
- **Boundary value analysis:** Test at the edges of valid ranges (min, max, min-1, max+1)
- **Negative testing:** Invalid inputs, missing fields, wrong types, SQL injection, XSS
- **Cross-browser/responsive testing:** Cover major browsers and viewport sizes

### Test Case Table Format

| ID | Category | Test Case | Input | Expected Result |
|----|----------|-----------|-------|-----------------|
| XX-01 | Happy Path | Valid scenario | Valid data | Success behavior |
| XX-02 | Edge Case | Boundary input | Edge value | Correct handling |
| XX-03 | Negative | Invalid input | Bad data | Error message |

### Bug Report Template

| Field | Detail |
|-------|--------|
| **Title** | Clear, specific description |
| **Severity** | Critical / High / Medium / Low |
| **Priority** | P0 / P1 / P2 / P3 |
| **Component** | Affected module or feature |
| **Environment** | Browser, OS, version |

**Steps to Reproduce:**
1. Step-by-step actions
2. Include exact input values
3. Note any preconditions

**Expected:** What should happen
**Actual:** What actually happened
**Impact:** Business/user impact of the bug
**Suggested Fix:** Technical recommendation

### Severity and Priority Guide

- **Critical (P0):** Production down, data loss, security vulnerability
- **High (P1):** Major feature broken, significant user impact
- **Medium (P2):** Feature degraded, workaround exists
- **Low (P3):** Minor inconvenience, cosmetic issues

### Testing Checklist

- [ ] All must-have requirements have at least one test case
- [ ] Top 3 negative scenarios covered per feature
- [ ] Edge cases for all input fields (empty, max length, special characters)
- [ ] Authentication and authorization tested
- [ ] Error messages are clear and actionable
- [ ] Performance under expected load verified

### Rules

- Always categorize test cases: happy path, edge case, negative, destructive
- Include preconditions and test data requirements for every test case
- Rate bugs by severity and priority with reasoning
- Bug reports must include: steps to reproduce, expected vs. actual, environment
- Never mark a feature as "tested" without covering at least the top 3 negative scenarios
- Write test cases that a junior QA engineer could execute without asking questions
