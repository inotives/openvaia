---
name: bug_analysis
description: Systematic bug investigation framework with root cause analysis and debugging workflows
tags: [development, debugging, troubleshooting]
source: awesome-openclaw-agents/development/bug-hunter
---

## Bug Analysis

> ~678 tokens

### Root Cause Analysis Framework

For every bug, work through these five questions in order:

1. **What happened?** — Error message, symptoms, user impact, scope (one user vs all)
2. **When did it start?** — Timestamp, correlation with recent changes/deployments
3. **Where in the code?** — Stack trace, file, line, function, call chain
4. **Why did it happen?** — Root cause (not just the symptom)
5. **How to fix?** — Immediate fix AND long-term prevention

### Debugging Workflow

1. Parse the error message and stack trace
2. Identify root cause vs symptoms — the first error in the log is not always the root cause
3. Rank likely causes by probability (assign rough percentages)
4. Map error to the relevant source code path
5. Check if it is a known issue or regression (search issues, recent commits)
6. Suggest debugging steps in order of likelihood
7. Provide test cases to reproduce the bug
8. Recommend both a fix and a preventive measure

### Common Bug Categories

**Null/Undefined References**
- Missing null checks on API responses
- Optional chaining not used on nested objects
- Default values not set for function parameters

**Environment Differences (works locally, fails in production)**
- Missing environment variables
- Different runtime versions (Node, Python, etc.)
- Build mode vs dev mode behavior differences
- Database connectivity (localhost vs external, SSL requirements)
- File paths (absolute vs relative, case sensitivity)

**Race Conditions**
- Concurrent writes to same resource
- Async operations completing out of order
- Missing locks or transaction isolation

**Error Handling Gaps**
- Unhandled promise rejections
- Missing catch blocks on network calls
- Silent failures (error caught but not logged)

### Bug Report Template

```
## Bug Report

**Error:** <exact error message>
**Impact:** <who/what is affected, severity>
**First seen:** <timestamp or deployment>

### Analysis

**Root cause:** <explanation>
**Evidence:** <stack trace, logs, code references>

### Likely Causes (ranked)
1. <cause> (<probability>%) — <reasoning>
2. <cause> (<probability>%) — <reasoning>

### Reproduction Steps
1. <step>
2. <step>

### Fix
**Immediate:** <what to change>
**Prevention:** <test, guard, or process to prevent recurrence>
```

### Debugging Guidelines

- Start with the most likely cause, not the most interesting one
- Provide evidence for every hypothesis
- Always include reproduction steps
- Check for similar past bugs before deep-diving
- Check recent deployments and git blame on affected files
- Suggest both a fix and a preventive measure (test, monitoring, guard)
- Never provide fixes without understanding the cause first
- Do not assume the first error in the log is the root cause
- Account for environment differences (dev vs staging vs prod)
