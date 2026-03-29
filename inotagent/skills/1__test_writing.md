---
name: test_writing
description: Test generation guidelines covering unit, integration, and E2E tests with coverage strategy
tags: [development, testing, quality]
source: awesome-openclaw-agents/development/test-writer
---

## Test Writing

> ~395 tokens

### Coverage Strategy

For every function or endpoint, write at minimum:

1. **Happy path** — valid input produces expected output
2. **Error path** — invalid input or failure condition handled correctly
3. **Edge case** — boundary values, empty inputs, large inputs, concurrency

### Test Types

**Unit Tests**
- Test individual functions in isolation
- Mock external dependencies (DB, APIs, file system)
- Fast execution, run on every commit

**Integration Tests**
- Test interactions between components (API endpoint + DB)
- Use realistic fixtures and test data factories
- Run on PR and pre-deploy

**End-to-End Tests**
- Test critical user flows through the full stack
- Use tools like Playwright or Cypress
- Run on pre-deploy and scheduled

### Identifying Untested Code

When auditing test coverage, prioritize these untested paths:

- Authentication and authorization flows (token refresh, expired tokens, disabled accounts)
- Error handling branches (what happens when the DB is down, API returns 500)
- Rate limiting and throttling logic
- Data validation edge cases (SQL injection, XSS payloads, malformed input)
- Concurrent operation handling (race conditions, duplicate submissions)
- Scheduled job and background task logic

### Test Quality Rules

- Test behavior, not implementation — tests should survive refactoring
- Assertions should be meaningful (check actual values, not just "no error")
- Test names should describe the scenario, not the function name
- Avoid testing framework internals or third-party library behavior
- Each test should be independent — no shared mutable state between tests
- Use test data factories over hardcoded fixtures for maintainability
