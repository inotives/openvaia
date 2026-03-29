---
name: issue_triage
description: Triage GitHub issues with auto-labeling, priority assignment, duplicate detection, and team routing.
tags: [development, github, issues, triage]
source: awesome-openclaw-agents/agents/development/github-issue-triager
---

## Issue Triage

> ~694 tokens

### Auto-Labeling Workflow

1. Classify issues by type: bug, feature, enhancement, question, documentation
2. Add component labels based on file paths and keywords mentioned
3. Apply platform labels (iOS, Android, web, API, CLI)
4. Tag with affected version when mentioned
5. Add "good-first-issue" to well-scoped, low-complexity items

### Priority Assignment Framework

| Priority | Criteria | Examples |
|----------|----------|---------|
| P0 (Critical) | Production down, data loss, security vulnerability | Auth bypass, DB corruption |
| P1 (High) | Major feature broken, significant user impact | Login failures, payment errors |
| P2 (Medium) | Feature degraded, workaround exists | Slow search, UI glitch with workaround |
| P3 (Low) | Minor inconvenience, cosmetic issues | Typo, alignment off by 1px |
| P4 (Wishlist) | Nice-to-have, future consideration | Feature suggestions |

### Duplicate Detection Checklist

1. Compare new issues against open issues using title and description similarity
2. Check against recently closed issues (last 90 days)
3. Link potential duplicates with a comment explaining the match
4. Close newer duplicate with reference to the original
5. Track frequently reported issues and suggest FAQ entries
6. Bump priority if multiple reports of the same issue appear

### Team Routing Rules

- Route to the correct team based on component labels
- Consider current workload when assigning individuals
- Respect on-call rotation for P0/P1 issues
- Escalate to team lead if no one is available
- Balance assignments across team members over time

### Triage Comment Format

```
Issue Triage -- #<number>

Labels: <type>, <component>, <platform>, <priority>
Assignee: @<user> (<team>, <N> open issues)

Reasoning:
- Type: <classification with evidence>
- Priority: <level with justification>
- Component: <area with evidence>
- Duplicates: <found/not found>

Similar issues:
- #<number> (<status>) -- <relationship>

Next steps:
- <action items>
```

### Weekly Report Format

```
SUMMARY: New: X, Closed: Y, Net: +/-Z (N total open)
BY PRIORITY: P0-P4 breakdown with new/resolved counts
BY TYPE: Bugs, Features, Questions, Docs with percentages
METRICS: Avg time to first response, avg time to close, stale count
ATTENTION NEEDED: Issues requiring escalation or re-prioritization
```

### Rules

- Triage every new issue promptly
- Never close an issue without a comment explaining why
- Always check for duplicates before labeling as new
- Priority assignments must include reasoning
- Bug reports without reproduction steps get "needs-info" label, not rejection
- Feature requests always get acknowledged, even if deprioritized
- Security-related issues get "security" label and immediate routing
- First-time contributors get a welcome message
