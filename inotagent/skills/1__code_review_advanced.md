---
name: code_review_advanced
description: Structured code review workflow with severity classification and security scanning
tags: [development, review, security, quality]
source: awesome-openclaw-agents/development/code-reviewer
---

## Code Review

> ~631 tokens

### Review Workflow

1. **Security scan** — check for vulnerabilities before anything else
2. **Logic review** — look for bugs, edge cases, and logic errors
3. **Performance check** — identify bottlenecks and inefficiencies
4. **Quality assessment** — rate overall quality, check duplication and complexity
5. **Style review** — only after all substantive issues are addressed

### Severity Classification

Categorize every finding into one of these levels:

- **Critical** — Bug, security vulnerability, data loss risk. Must fix before merge.
- **Warning** — Performance issue, error handling gap, logic concern. Should fix.
- **Suggestion** — Better pattern, cleaner approach, readability improvement. Nice to have.
- **Nitpick** — Style preference, naming, formatting. Lowest priority, never block on these.

Always lead with the most critical issues. Do not nitpick style when real bugs exist.

### Security Scanning Checklist

- [ ] SQL injection risks (raw queries, string concatenation)
- [ ] XSS vulnerabilities (unescaped user input in HTML/templates)
- [ ] Command injection (shell commands with user input)
- [ ] Hardcoded secrets or credentials in source code
- [ ] Insecure dependencies (known CVEs)
- [ ] Authentication logic flaws (timing attacks, weak comparisons)
- [ ] Authorization gaps (missing permission checks)
- [ ] Information leakage in error messages (e.g., "invalid password" vs "invalid email")
- [ ] Rate limiting on sensitive endpoints (login, password reset)
- [ ] JWT/token handling (hardcoded secrets, expiration, refresh logic)

### Quality Assessment Checklist

- [ ] Test coverage — are there gaps for new/changed code paths?
- [ ] Code duplication — repeated logic that should be extracted
- [ ] Function complexity — overly long or deeply nested functions
- [ ] Error handling — are all failure paths covered?
- [ ] Input validation — are all external inputs validated?
- [ ] Resource cleanup — are connections, files, streams properly closed?

### Review Output Format

```
Code Review — <filename>

Overall: <grade A-F> (<one-line summary>)

CRITICAL (<count>):
- <file>:<line> — <description>
  Fix: <suggested fix>

WARNING (<count>):
- <file>:<line> — <description>

SUGGESTION (<count>):
- <description>

GOOD:
- <what was done well>
```

### Guidelines

- Provide code examples for suggested fixes
- Acknowledge good patterns and improvements
- Explain the "why" behind every suggestion
- Be specific about file names and line numbers
- Do not rewrite entire functions without asking
- Do not block PRs for minor style preferences
- Consider context: quick fix vs deliberate refactor
