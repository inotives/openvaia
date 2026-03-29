---
name: test_driven_development
description: RED-GREEN-REFACTOR cycle enforcement — no production code without a failing test first
tags: [testing, development, tdd]
source: superpowers/obra/superpowers
---
# Test-Driven Development (TDD)

Use when implementing any feature or bugfix — before writing implementation code.

## Core Principle

**If you didn't watch the test fail, you don't know if it tests the right thing.**

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it. Start over. No exceptions.

## Red-Green-Refactor Cycle

### RED — Write Failing Test

Write one minimal test showing what should happen.

- One behavior per test
- Clear descriptive name ("and" in name? split it)
- Use real code, not mocks (unless unavoidable)

### Verify RED — Watch It Fail (MANDATORY)

Run the test. Confirm:
- Test fails (not errors)
- Failure message is expected
- Fails because feature is missing (not typos)

Test passes immediately? You're testing existing behavior. Fix the test.

### GREEN — Minimal Code

Write the simplest code to pass the test.

- Don't add features beyond what the test requires
- Don't refactor other code
- Don't "improve" beyond the test
- YAGNI — no options, no config, no extensibility

### Verify GREEN — Watch It Pass (MANDATORY)

Run the test. Confirm:
- Test passes
- Other tests still pass
- Output is clean (no errors, warnings)

Test fails? Fix code, not test. Other tests fail? Fix now.

### REFACTOR — Clean Up

Only after green:
- Remove duplication
- Improve names
- Extract helpers

Keep tests green. Don't add behavior.

### Repeat

Next failing test for next behavior.

## Why Order Matters

| Excuse | Reality |
|--------|---------|
| "I'll test after" | Tests passing immediately prove nothing — you never saw it catch the bug |
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "Already manually tested" | Ad-hoc ≠ systematic. No record, can't re-run. |
| "Deleting X hours is wasteful" | Sunk cost fallacy. Keeping unverified code is technical debt. |
| "Need to explore first" | Fine. Throw away exploration, start fresh with TDD. |
| "Test too hard to write" | Listen to the test. Hard to test = hard to use. Simplify design. |
| "TDD will slow me down" | TDD is faster than debugging. |
| "Keep as reference" | You'll adapt it. That's testing after. Delete means delete. |

## Bug Fix Example

**Bug:** Empty email accepted

**RED:**
```
test('rejects empty email', async () => {
  const result = await submitForm({ email: '' });
  expect(result.error).toBe('Email required');
});
```

**Verify RED:** `FAIL: expected 'Email required', got undefined`

**GREEN:**
```
function submitForm(data) {
  if (!data.email?.trim()) return { error: 'Email required' };
  // ...
}
```

**Verify GREEN:** `PASS`

**REFACTOR:** Extract validation for multiple fields if needed.

## Testing Anti-Patterns

Avoid these common mistakes:
- Testing mock behavior instead of real behavior
- Adding test-only methods to production classes
- Mocking without understanding dependencies
- Huge test setup (= design too complex, simplify)
- Tests coupled to implementation details

## When Stuck

| Problem | Solution |
|---------|----------|
| Don't know how to test | Write wished-for API. Write assertion first. |
| Test too complicated | Design too complicated. Simplify interface. |
| Must mock everything | Code too coupled. Use dependency injection. |
| Test setup huge | Extract helpers. Still complex? Simplify design. |

## Verification Checklist

Before marking work complete:
- [ ] Every new function/method has a test
- [ ] Watched each test fail before implementing
- [ ] Each test failed for expected reason
- [ ] Wrote minimal code to pass each test
- [ ] All tests pass with clean output
- [ ] Tests use real code (mocks only if unavoidable)
- [ ] Edge cases and errors covered

Can't check all boxes? You skipped TDD. Start over.
