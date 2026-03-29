---
name: code_review
description: Self-review checklist before raising PRs — security, quality, correctness
tags: [review, quality]
source: openvaia/v1-migration-seed
---

## Code Review (Self-Review)

> ~270 tokens
Before raising a PR, review your own changes:

**Security:**
- [ ] No secrets, tokens, or API keys in code
- [ ] No hardcoded credentials or connection strings
- [ ] User input is validated at boundaries

**Quality:**
- [ ] No debug prints, console.logs, or TODO comments left behind
- [ ] No unused imports or dead code
- [ ] Variable names are clear and descriptive
- [ ] Functions do one thing and are reasonably sized

**Correctness:**
- [ ] Edge cases handled (empty lists, None values, missing keys)
- [ ] Error handling is appropriate -- not swallowing exceptions silently
- [ ] Database queries use parameterized values (no SQL injection)

**Compatibility:**
- [ ] Existing tests still pass
- [ ] No breaking changes to public interfaces without coordination
- [ ] Migration files include both up and down sections

**Run the check:**
```
shell(command="cd /workspace/repos/<repo-name> && git diff --cached --stat")
```
Review each changed file before committing.
