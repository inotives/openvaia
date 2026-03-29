---
name: finishing_dev_branch
description: Guide branch completion — verify tests, present merge/PR/keep/discard options, cleanup
tags: [git, workflow, development]
source: superpowers/obra/superpowers
---
# Finishing a Development Branch

Guide completion of development work by presenting clear options and handling the chosen workflow.

## Core Principle

**Verify tests → Present options → Execute choice → Clean up.**

## The Process

### Step 1: Verify Tests

Run the project's test suite. If tests fail, STOP — cannot proceed until tests pass.

```
Tests failing (N failures). Must fix before completing:
[Show failures]
```

### Step 2: Determine Base Branch

Identify what branch this work split from (usually `main` or `master`).

### Step 3: Present Options

Present exactly these 4 options:

```
Implementation complete. What would you like to do?

1. Merge back to <base-branch> locally
2. Push and create a Pull Request
3. Keep the branch as-is (I'll handle it later)
4. Discard this work

Which option?
```

### Step 4: Execute Choice

**Option 1 — Merge Locally:**
1. Switch to base branch, pull latest
2. Merge feature branch
3. Verify tests on merged result
4. Delete feature branch

**Option 2 — Push and Create PR:**
1. Push branch to remote
2. Create PR with summary + test plan
3. Keep branch alive for review

**Option 3 — Keep As-Is:**
- Report branch name and location
- Don't cleanup anything

**Option 4 — Discard:**
- Show what will be deleted (branch, commits)
- Require typed "discard" confirmation
- Delete branch only after confirmation

### Step 5: Cleanup

| Option | Merge | Push | Keep Branch | Cleanup |
|--------|-------|------|-------------|---------|
| 1. Merge locally | Yes | — | Delete | Yes |
| 2. Create PR | — | Yes | Keep | — |
| 3. Keep as-is | — | — | Keep | — |
| 4. Discard | — | — | Force delete | Yes |

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Skip test verification | Always verify tests before offering options |
| Open-ended "what next?" | Present exactly 4 structured options |
| Delete work without confirmation | Require typed "discard" for Option 4 |
| Force-push without request | Never force-push unless explicitly asked |
| Merge with failing tests | STOP — fix tests first |

## Red Flags

**Never:**
- Proceed with failing tests
- Merge without verifying tests on the result
- Delete work without typed confirmation
- Force-push without explicit request

**Always:**
- Verify tests before offering options
- Present exactly 4 options
- Get confirmation for destructive actions
