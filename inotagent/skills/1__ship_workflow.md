---
name: ship_workflow
description: Pre-merge shipping workflow — test, review diff, version bump, changelog, bisectable commits, PR creation
tags: [shipping, git, workflow]
source: gstack/garrytan/gstack
---
# Ship Workflow

Structured pre-merge validation: test on merged code, review readiness, version bump, changelog, create PR.

## When to Use

- Ready to merge a feature branch
- Preparing a release
- Creating a PR for review

## The Process

### Step 1: Pre-Flight Checks
- Confirm correct branch
- Check for uncommitted changes
- Verify review status (has code been reviewed?)

### Step 2: Merge Base Branch
```
git fetch origin main
git merge origin/main
```
Resolve conflicts if any. All subsequent tests run on merged code.

### Step 3: Run Tests
Run full test suite on the merged result. If tests fail, fix before proceeding.

### Step 4: Pre-Landing Review
If no prior review exists, run a self-review:
- Scope drift detection (diff vs plan)
- Critical issues (SQL safety, auth, race conditions)
- Test coverage trace

### Step 5: Plan Completion Audit
If a plan file exists, verify every task is checked off. Incomplete plan = not ready to ship.

### Step 6: Version Bump + Changelog
- Bump version appropriately (patch/minor/major)
- Generate changelog entry from commits since last release
- Include: what changed, why, migration notes if any

### Step 7: Bisectable Commit History
Review commit history:
- Each commit should be a single logical change
- Squash "fix typo" and "wip" commits
- Result: every commit independently revertable

### Step 8: Create PR
```
git push -u origin <branch>
gh pr create --title "<title>" --body "<summary + test plan>"
```

## Review Readiness Dashboard

Before creating PR, verify:

| Check | Status |
|-------|--------|
| Tests pass on merged code | Required |
| Code reviewed (self or peer) | Required |
| Plan tasks complete | Required (if plan exists) |
| No critical issues open | Required |
| Version bumped | Required (for releases) |
| Changelog updated | Required (for releases) |
| Commits bisectable | Recommended |

## Rules

- Never ship with failing tests
- Never skip the merge-base step (test on merged code, not just your branch)
- Each commit should be independently revertable
- Changelog describes WHY, not just WHAT
