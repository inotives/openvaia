---
name: subagent_driven_development
description: Execute plans with fresh subagent per task and two-stage review (spec compliance + code quality)
tags: [development, delegation, workflow]
source: superpowers/obra/superpowers
---
# Subagent-Driven Development

Execute implementation plans by dispatching a fresh subagent per task, with two-stage review after each.

## Core Principle

Fresh subagent per task + two-stage review (spec compliance then code quality) = high quality, fast iteration.

## When to Use

- You have an implementation plan with independent tasks
- Tasks can be executed in the current session
- Each task produces self-contained changes

## The Process

### 1. Read Plan and Extract Tasks
- Read the plan file once
- Extract all tasks with full text and context
- Track progress as tasks complete

### 2. Per Task: Dispatch → Review → Approve

**Dispatch implementer:**
- Provide full task text + project context
- Subagent implements, tests, commits, and self-reviews
- If subagent asks questions, answer them before proceeding

**Stage 1 — Spec compliance review:**
- Does the code match the spec exactly?
- Nothing missing, nothing extra
- If issues found → implementer fixes → re-review

**Stage 2 — Code quality review:**
- Code well-structured, readable, tested?
- No anti-patterns, magic numbers, poor naming?
- If issues found → implementer fixes → re-review

**Mark task complete** only when both reviews pass.

### 3. After All Tasks
- Dispatch final reviewer for entire implementation
- Verify all requirements met end-to-end

## Model Selection

Use the least powerful model that can handle each role:

| Task Type | Model Tier | Examples |
|-----------|-----------|---------|
| Mechanical implementation | Fast/cheap | Isolated functions, clear specs, 1-2 files |
| Integration work | Standard | Multi-file coordination, pattern matching |
| Architecture/design/review | Most capable | Design judgment, broad codebase understanding |

## Handling Implementer Status

| Status | Action |
|--------|--------|
| **DONE** | Proceed to spec review |
| **DONE_WITH_CONCERNS** | Read concerns, address if about correctness, then review |
| **NEEDS_CONTEXT** | Provide missing context, re-dispatch |
| **BLOCKED** | Assess: provide context → re-dispatch with better model → break task smaller → escalate to human |

Never force the same model to retry without changes.

## Prompt Structure for Subagents

Good subagent prompts are:
1. **Focused** — One clear task scope
2. **Self-contained** — All context needed to understand the task
3. **Specific about output** — What should the subagent return?

Include: task description, relevant file paths, expected behavior, constraints, and what to return.

## Red Flags — Never Do These

- Skip reviews (spec compliance OR code quality)
- Proceed with unfixed issues
- Dispatch parallel implementation subagents (file conflicts)
- Let subagent read plan file (provide full text instead)
- Skip context (subagent needs to understand where task fits)
- Ignore subagent questions
- Accept "close enough" on spec compliance
- Start code quality review before spec compliance passes
- Move to next task while reviews have open issues

## Quality Gates

| Gate | Purpose |
|------|---------|
| Self-review by implementer | Catches obvious issues before handoff |
| Spec compliance review | Prevents over/under-building |
| Code quality review | Ensures implementation is well-built |
| Final review | Verifies end-to-end integration |

## Advantages Over Manual Execution

- Fresh context per task (no confusion from prior work)
- Subagents follow TDD naturally
- Parallel-safe (subagents don't interfere)
- Review checkpoints are automatic
- Catches issues early (cheaper than debugging later)
