---
name: testing_practices
description: Robin testing workflow — run before push, write for new code, check coverage
tags: [testing, quality]
source: openvaia/v1-migration-seed
---

## Testing Practices

> ~257 tokens

**Before every push:**
1. Run the full test suite:
   ```
   shell(command="cd /workspace/repos/<repo-name> && make test", timeout=300)
   ```
   If no `make test`, find the test command in the repo's CLAUDE.md or README.
2. If tests fail, fix them before pushing -- never push broken tests.

**When writing new code:**
3. Write tests for new functions and endpoints -- at minimum, test the happy path.
4. Place tests alongside existing test files -- follow the repo's test structure.
5. Test edge cases: empty input, missing data, error responses.

**When fixing bugs:**
6. Write a failing test first that reproduces the bug.
7. Fix the bug, verify the test passes.
8. This prevents regressions.

**What NOT to test:**
- Don't test third-party libraries
- Don't test trivial getters/setters
- Don't mock everything -- prefer integration tests for DB-touching code
