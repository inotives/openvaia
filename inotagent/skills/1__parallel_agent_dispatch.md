---
name: parallel_agent_dispatch
description: Dispatch concurrent agents for independent tasks — one agent per problem domain
tags: [delegation, parallelism, workflow]
source: superpowers/obra/superpowers
---
# Dispatching Parallel Agents

Use when facing 2+ independent tasks that can be worked on without shared state or sequential dependencies.

## Core Principle

Dispatch one agent per independent problem domain. Let them work concurrently. When you have multiple unrelated failures or tasks, investigating them sequentially wastes time.

## When to Use

- 3+ tasks/failures across different files or subsystems
- Each problem can be understood independently
- No shared state between investigations
- Agents won't interfere with each other (not editing same files)

## When NOT to Use

- Failures are related (fix one might fix others)
- Need to understand full system state first
- Exploratory debugging (don't know what's broken yet)
- Shared state (agents editing same files/resources)

## The Pattern

### 1. Identify Independent Domains

Group tasks/failures by what's affected:
- Domain A: Authentication flow
- Domain B: Data pipeline
- Domain C: UI rendering

Each domain is independent — fixing one doesn't affect the others.

### 2. Create Focused Agent Prompts

Each agent gets:
- **Specific scope** — One file, subsystem, or problem domain
- **Clear goal** — What to fix or implement
- **All context needed** — Error messages, test names, relevant code
- **Constraints** — Don't change code outside scope
- **Expected output** — Summary of findings and changes

### 3. Dispatch Concurrently

Send all agents at once. Each works in isolation with fresh context.

### 4. Review and Integrate

When agents return:
1. **Read each summary** — Understand what changed
2. **Check for conflicts** — Did agents edit the same code?
3. **Run full test suite** — Verify all fixes work together
4. **Spot check** — Agents can make systematic errors

## Agent Prompt Quality

**Good prompt:**
- Focused: "Fix agent-tool-abort.test.ts" (specific scope)
- Context: Paste error messages and test names
- Constraints: "Do NOT change production code"
- Output: "Return summary of root cause and changes"

**Bad prompt:**
- Too broad: "Fix all the tests"
- No context: "Fix the race condition"
- No constraints: Agent might refactor everything
- Vague output: "Fix it"

## Example

**Scenario:** 6 test failures across 3 files after refactoring

**Dispatch:**
```
Agent 1 → Fix agent-tool-abort.test.ts (3 timing failures)
Agent 2 → Fix batch-completion.test.ts (2 execution failures)
Agent 3 → Fix race-conditions.test.ts (1 count failure)
```

**Results:**
- Agent 1: Replaced timeouts with event-based waiting
- Agent 2: Fixed event structure bug
- Agent 3: Added wait for async execution

All fixes independent, no conflicts, full suite green. 3 problems solved in time of 1.

## Key Benefits

| Benefit | Why |
|---------|-----|
| Parallelization | Multiple investigations happen simultaneously |
| Focus | Each agent has narrow scope, less confusion |
| Independence | Agents don't interfere with each other |
| Speed | N problems solved in time of 1 |
| Fresh context | Each agent starts clean, no context pollution |
