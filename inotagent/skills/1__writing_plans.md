---
name: writing_plans
description: Break specs into bite-sized implementation tasks with complete code, exact paths, and TDD steps
tags: [planning, development, workflow]
source: superpowers/obra/superpowers
---
# Writing Implementation Plans

Use when you have a spec or requirements for a multi-step task — before touching code.

## Core Principle

Write comprehensive plans assuming the implementer has zero codebase context. Document everything: which files to touch, complete code, exact commands, expected output. Break into bite-sized tasks (2-5 minutes each). DRY. YAGNI. TDD. Frequent commits.

## Scope Check

If the spec covers multiple independent subsystems, break into separate plans — one per subsystem. Each plan should produce working, testable software on its own.

## File Structure First

Before defining tasks, map out which files will be created or modified:
- Each file should have one clear responsibility
- Prefer smaller, focused files over large ones
- Files that change together should live together
- Follow existing codebase patterns

## Bite-Sized Task Granularity

Each step is one action (2-5 minutes):
1. "Write the failing test" — step
2. "Run it to make sure it fails" — step
3. "Implement the minimal code to make the test pass" — step
4. "Run the tests and make sure they pass" — step
5. "Commit" — step

## Task Structure

Each task should include:
- **Files**: Exact paths to create, modify, and test
- **Step-by-step**: With complete code blocks (not pseudocode)
- **Commands**: Exact run commands with expected output
- **Commit**: What to commit and the commit message

## No Placeholders

Every step must contain actual content. These are plan failures — never write them:
- "TBD", "TODO", "implement later"
- "Add appropriate error handling"
- "Write tests for the above" (without actual test code)
- "Similar to Task N" (repeat the code — tasks may be read independently)
- Steps that describe what to do without showing how
- References to types/functions not defined in any task

## Plan Header Template

```markdown
# [Feature Name] Implementation Plan

**Goal:** [One sentence]
**Architecture:** [2-3 sentences about approach]
**Tech Stack:** [Key technologies]

---
```

## Self-Review Checklist

After writing the plan, review with fresh eyes:

1. **Spec coverage** — Can you point to a task for each requirement? List gaps.
2. **Placeholder scan** — Any "TBD", vague descriptions, missing code blocks?
3. **Type consistency** — Do names/signatures in later tasks match earlier tasks?
4. **Completeness** — Every step has code, commands, and expected output?

Fix issues inline. If a spec requirement has no task, add one.

## Execution Options

After the plan is complete, offer:

1. **Subagent-Driven** (recommended) — Fresh subagent per task, two-stage review (spec compliance then code quality), fast iteration
2. **Sequential Execution** — Execute tasks in order with checkpoints for human review

## Key Rules

- Exact file paths always
- Complete code in every step
- Exact commands with expected output
- One behavior per test, one fix per step
- Commit after each task completes
- DRY, YAGNI, TDD throughout
