---
name: spec_verification
description: Verify implementation against spec — check every requirement and scenario, generate evidence-based report
tags: [verification, quality, testing]
source: openspec/Fission-AI/OpenSpec
---
# Spec Verification

After implementation, systematically verify every requirement in the spec. Generates an evidence-based verification report — not "it works" but "here's proof for each requirement."

## When to Use

- After implementation is complete
- Before claiming a feature is done
- Before merging / shipping
- When human asks "is it done?"

## Process

### Step 1: Load the Spec
```
research_search(tags=["spec"], query="[feature name]")
```
Read the full spec with all requirements and scenarios.

### Step 2: Verify Each Requirement

For every requirement in the spec:

1. **Find the implementation** — which files/functions implement this?
2. **Check each scenario** — does the Given/When/Then match actual behavior?
3. **Verify via evidence:**
   - Automated test exists and passes → `PASS`
   - Manual verification confirms behavior → `PASS`
   - Behavior doesn't match scenario → `FAIL`
   - Partially implemented → `PARTIAL`
   - No test or verification done → `NOT TESTED`

### Step 3: Generate Report

```markdown
# Verification Report: [Feature Name]

## Summary
- **Spec:** SPEC: [name]
- **Total requirements:** N
- **Passed:** X
- **Failed:** Y
- **Partial:** Z
- **Not tested:** W

## Results

### Requirement: [Name] — PASS ✅
- ✅ Scenario: [Happy Path] — verified via [test name / manual check]
- ✅ Scenario: [Edge Case] — verified via [evidence]

### Requirement: [Name] — FAIL ❌
- ✅ Scenario: [Happy Path] — verified
- ❌ Scenario: [Error Case] — [what's wrong: expected X, got Y]

### Requirement: [Name] — PARTIAL ⚠️
- ✅ Scenario: [Main Flow] — verified
- ⚠️ Scenario: [Edge Case] — not implemented yet

### Requirement: [Name] — NOT TESTED 🔲
- 🔲 No automated test exists
- 🔲 Manual verification not performed

## Action Items
1. [What needs to be fixed — MUST]
2. [What needs testing — SHOULD]

## Verdict
[PASS — all requirements verified / FAIL — X requirements need work / PARTIAL — ready with caveats]
```

### Step 4: Store Report
```
research_store(
  title="VERIFY: [Feature Name]",
  body="[full verification report]",
  tags=["verification", "<domain-tags>"]
)
```

## Verification Methods

| Method | When to Use | Evidence |
|--------|------------|---------|
| **Automated test** | Test exists and covers the scenario | Test name + pass result |
| **Manual test** | Run the feature, observe behavior | Description of what you did and saw |
| **Code review** | Verify logic handles the scenario | File:line reference |
| **Shell command** | API endpoint or CLI behavior | Command + output |

## Key Principles

- **Every requirement gets a verdict** — no skipping, no "probably works"
- **Evidence, not assertions** — "test passes" beats "should work"
- **FAIL is useful** — finding failures before shipping is the whole point
- **NOT TESTED is honest** — better than pretending you verified something you didn't
- **Action items are specific** — "fix X in file Y" not "needs work"

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| "Tests pass, so it's done" | Tests may not cover all spec scenarios — check each one |
| Skipping edge case scenarios | Edge cases are where bugs hide — verify them |
| No evidence for PASS | State HOW you verified — test name, command, or observation |
| Marking PARTIAL as PASS | Be honest — partial is partial |
| Forgetting error scenarios | Error handling is a requirement too |
