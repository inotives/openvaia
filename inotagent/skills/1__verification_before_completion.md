---
name: verification_before_completion
description: Evidence before claims — run verification commands and confirm output before any completion claims
tags: [quality, verification, workflow]
source: superpowers/obra/superpowers
---
# Verification Before Completion

Claiming work is complete without verification is dishonesty, not efficiency.

## Core Principle

**Evidence before claims, always.**

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't run the verification command, you cannot claim it passes.

## The Gate Function

Before claiming any status or expressing satisfaction:

1. **IDENTIFY** — What command proves this claim?
2. **RUN** — Execute the FULL command (fresh, complete)
3. **READ** — Full output, check exit code, count failures
4. **VERIFY** — Does output confirm the claim?
   - If NO: State actual status with evidence
   - If YES: State claim WITH evidence
5. **ONLY THEN** — Make the claim

Skip any step = lying, not verifying.

## What Each Claim Requires

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | Test command output: 0 failures | Previous run, "should pass" |
| Linter clean | Linter output: 0 errors | Partial check, extrapolation |
| Build succeeds | Build command: exit 0 | Linter passing, "logs look good" |
| Bug fixed | Test original symptom: passes | Code changed, assumed fixed |
| Regression test works | Red-green cycle verified | Test passes once |
| Requirements met | Line-by-line checklist | Tests passing |

## Key Patterns

**Tests:**
```
OK:  [Run test command] [See: 34/34 pass] "All tests pass"
BAD: "Should pass now" / "Looks correct"
```

**Regression tests (TDD Red-Green):**
```
OK:  Write → Run (pass) → Revert fix → Run (MUST FAIL) → Restore → Run (pass)
BAD: "I've written a regression test" (without red-green verification)
```

**Build:**
```
OK:  [Run build] [See: exit 0] "Build passes"
BAD: "Linter passed" (linter doesn't check compilation)
```

**Requirements:**
```
OK:  Re-read plan → Create checklist → Verify each → Report gaps or completion
BAD: "Tests pass, phase complete"
```

## Red Flags — STOP

If you catch yourself:
- Using "should", "probably", "seems to"
- Expressing satisfaction before verification ("Great!", "Done!")
- About to commit/push/PR without verification
- Relying on partial verification
- Thinking "just this once"
- ANY wording implying success without having run verification

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Should work now" | RUN the verification |
| "I'm confident" | Confidence ≠ evidence |
| "Just this once" | No exceptions |
| "Linter passed" | Linter ≠ compiler |
| "Partial check is enough" | Partial proves nothing |

## When to Apply

**ALWAYS before:**
- Any success/completion claims
- Committing, PR creation, task completion
- Moving to next task
- Any positive statement about work state

## The Bottom Line

Run the command. Read the output. THEN claim the result. Non-negotiable.
