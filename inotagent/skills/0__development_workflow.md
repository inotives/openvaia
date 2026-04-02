---
name: development_workflow
description: Workflow routing — guides which skills and steps to follow based on task type and complexity
tags: [workflow, orchestration, global]
source: openvaia/ES-0013
---
# Development Workflow

When you receive a task, follow this routing to decide which steps and skills to use. Not every task needs every step — scale the process to the complexity.

## Step 1: Assess Task Type & Complexity

| Type | Examples | Complexity |
|------|----------|-----------|
| **Quick fix** | Typo, config change, minor bug | Low |
| **Small feature** | Add pagination, new API field, UI tweak | Low-Medium |
| **Medium feature** | New endpoint, new UI page, integration | Medium |
| **Large feature** | New system, multi-component change, architecture | High |
| **Research** | Market analysis, API evaluation, data gathering | Varies |
| **Operations** | Health check, monitoring, deployment | Low |

## Step 2: Follow the Workflow for That Complexity

### Quick Fix
```
1. Understand the issue
2. Write a plan (writing_plans skill)
3. Implement with TDD (test_driven_development skill)
4. Verify (verification_before_completion skill)
5. Done
```

### Small Feature
```
1. Write a plan with tasks (writing_plans skill)
2. Implement with TDD (test_driven_development skill)
3. Verify against plan (spec_verification skill)
4. Ship (ship_workflow / finishing_dev_branch skill)
```

### Medium Feature
```
1. Write proposal → store as "PROP: [name]" with tag "proposal"
   (spec_driven_proposal skill)
2. Get human approval on proposal
3. Write requirements → store as "SPEC: [name]" with tag "spec"
   (requirement_specification skill)
4. Write implementation plan (writing_plans skill)
5. Implement with TDD (test_driven_development skill)
6. Verify against spec → store as "VERIFY: [name]" with tag "verification"
   (spec_verification skill)
7. Ship (ship_workflow / finishing_dev_branch skill)
```

### Large Feature
```
1. Brainstorm approaches (brainstorming skill)
2. Write proposal → store as "PROP: [name]" with tag "proposal"
   (spec_driven_proposal skill)
3. Get human approval on proposal
4. Write requirements → store as "SPEC: [name]" with tag "spec"
   (requirement_specification skill)
5. Write technical design → store as "DESIGN: [name]" with tag "design"
   (technical_design_doc skill)
6. Get human approval on design
7. Write implementation plan (writing_plans skill)
8. Implement — consider subagent_driven_development for independent tasks
9. Verify against spec → store as "VERIFY: [name]" with tag "verification"
   (spec_verification skill)
10. Ship (ship_workflow / finishing_dev_branch skill)
```

### Research Task
```
1. Check existing resources first (resource_first_research skill — always on)
2. Search memory for prior work (memory_and_improvement skill — always on)
3. Conduct research using browser, shell, APIs
4. Store findings as research report (research_store tool)
5. Save key learnings to memory (memory_store tool)
```

### Operations Task
```
1. Run the required checks (shell tool)
2. Report findings
3. If issues found → create follow-up tasks
4. Store operations log as research report
```

## Step 3: Human Approval Gates

These steps require human approval before proceeding:

| Gate | When | What to Present |
|------|------|----------------|
| **After proposal** | Medium + Large features | Show `PROP:` document, ask "proceed?" |
| **After design** | Large features | Show `DESIGN:` document, ask "proceed?" |
| **Before shipping** | All features | Show `VERIFY:` report, ask "ready to merge?" |

If human is not available, save the document and create a task tagged `needs-review` for follow-up.

## Step 4: Document Storage Convention

All planning documents use standardized prefixes and tags:

| Document | Title Prefix | Tag | Tool |
|----------|-------------|-----|------|
| Proposal | `PROP:` | `proposal` | `research_store` |
| Requirement spec | `SPEC:` | `spec` | `research_store` |
| Technical design | `DESIGN:` | `design` | `research_store` |
| Verification report | `VERIFY:` | `verification` | `research_store` |

Search previous documents: `research_search(tags=["proposal"])` etc.

## Step 5: When Stuck

| Situation | Action |
|-----------|--------|
| Don't know complexity | Start as Medium, downgrade if simple |
| Unsure about approach | Use brainstorming skill first |
| Multiple approaches exist | Write proposal with alternatives, let human decide |
| Implementation hits unexpected issues | Use systematic_debugging skill |
| Can't verify a requirement | Mark as NOT TESTED in verification, flag for human |

## Key Rules

- **Never skip straight to implementation for medium/large tasks** — write at least a proposal first
- **Store documents with correct prefixes** — makes them searchable and trackable
- **Get human approval at gates** — don't assume approval
- **Scale the process** — quick fixes don't need proposals; large features need the full pipeline
- **When in doubt, do more planning** — 10 minutes of planning saves hours of rework
