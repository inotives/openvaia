---
name: systematic_debugging
description: Root cause analysis before proposing fixes — 4-phase debugging process with defense in depth
tags: [debugging, troubleshooting, development]
source: superpowers/obra/superpowers
---
# Systematic Debugging

Use when encountering any bug, test failure, or unexpected behavior — before proposing fixes.

## Core Principle

**ALWAYS find root cause before attempting fixes. Symptom fixes are failure.**

NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST. If you haven't completed Phase 1, you cannot propose fixes.

## When to Use

Use for ANY technical issue: test failures, bugs, unexpected behavior, performance problems, build failures, integration issues.

Use ESPECIALLY when:
- Under time pressure (emergencies make guessing tempting)
- "Just one quick fix" seems obvious
- You've already tried multiple fixes
- Previous fix didn't work

## The Four Phases

Complete each phase before proceeding to the next.

### Phase 1: Root Cause Investigation

1. **Read Error Messages Carefully** — Don't skip past errors. Read stack traces completely. Note line numbers, file paths, error codes.
2. **Reproduce Consistently** — Can you trigger it reliably? What are the exact steps? If not reproducible, gather more data — don't guess.
3. **Check Recent Changes** — Git diff, recent commits, new dependencies, config changes, environmental differences.
4. **Gather Evidence in Multi-Component Systems** — For each component boundary: log what enters, log what exits, verify env/config propagation. Run once to gather evidence showing WHERE it breaks.
5. **Trace Data Flow (Root Cause Tracing)** — Trace backward through the call chain: observe symptom → find immediate cause → ask "what called this with bad data?" → keep tracing up → find original trigger → fix at source, not symptom.

### Phase 2: Pattern Analysis

1. **Find Working Examples** — Locate similar working code in the same codebase.
2. **Compare Against References** — Read reference implementations COMPLETELY, don't skim.
3. **Identify Differences** — List every difference between working and broken, however small.
4. **Understand Dependencies** — What components, settings, config, environment does this need?

### Phase 3: Hypothesis and Testing

1. **Form Single Hypothesis** — State clearly: "I think X is the root cause because Y."
2. **Test Minimally** — Make the SMALLEST possible change to test hypothesis. One variable at a time.
3. **Verify Before Continuing** — Worked? → Phase 4. Didn't work? → Form NEW hypothesis. Don't add more fixes on top.

### Phase 4: Implementation

1. **Create Failing Test Case** — Simplest possible reproduction. Automated test if possible. MUST have before fixing.
2. **Implement Single Fix** — Address root cause. ONE change at a time. No "while I'm here" improvements.
3. **Verify Fix** — Test passes? No other tests broken? Issue resolved?
4. **If Fix Doesn't Work** — Count fixes tried. If < 3: return to Phase 1. If ≥ 3: STOP and question the architecture.
5. **If 3+ Fixes Failed** — This is an architectural problem, not a bug. Question fundamentals: Is this pattern sound? Should we refactor vs. continue fixing symptoms? Discuss with human before more attempts.

## Defense in Depth

After fixing root cause, add validation at EVERY layer data passes through:

1. **Entry Point Validation** — Reject invalid input at API/function boundary
2. **Business Logic Validation** — Ensure data makes sense for the operation
3. **Environment Guards** — Prevent dangerous operations in wrong contexts
4. **Debug Instrumentation** — Capture context for forensics if it happens again

This makes the bug structurally impossible to recur, not just fixed for the current case.

## Condition-Based Waiting

When debugging flaky/timing issues, replace arbitrary delays with condition polling:
- Wait for the actual condition you care about, not a guess about timing
- Use polling with configurable timeout and clear error messages
- Arbitrary timeout is only correct AFTER waiting for a triggering condition

## Red Flags — STOP and Return to Phase 1

If you catch yourself thinking:
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Skip the test, I'll manually verify"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "One more fix attempt" (when already tried 2+)
- Proposing solutions before tracing data flow

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too. Process is fast for simple bugs. |
| "Emergency, no time for process" | Systematic debugging is FASTER than guess-and-check thrashing. |
| "Just try this first, then investigate" | First fix sets the pattern. Do it right from the start. |
| "Multiple fixes at once saves time" | Can't isolate what worked. Causes new bugs. |
| "I see the problem, let me fix it" | Seeing symptoms ≠ understanding root cause. |
| "One more fix attempt" (after 2+ failures) | 3+ failures = architectural problem. Question pattern, don't fix again. |
