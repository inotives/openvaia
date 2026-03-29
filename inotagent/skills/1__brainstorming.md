---
name: brainstorming
description: Design-first workflow — explore intent, propose approaches, get approval before any implementation
tags: [planning, design, workflow]
source: superpowers/obra/superpowers
---
# Brainstorming Ideas Into Designs

Use before any creative work — creating features, building components, adding functionality, or modifying behavior. Explores intent, requirements, and design before implementation.

## Hard Gate

Do NOT write any code, scaffold any project, or take any implementation action until you have presented a design and the user has approved it. This applies to EVERY project regardless of perceived simplicity.

## Anti-Pattern: "This Is Too Simple To Need A Design"

Every project goes through this process. A todo list, a single-function utility, a config change — all of them. "Simple" projects are where unexamined assumptions cause the most wasted work. The design can be short (a few sentences for truly simple projects), but you MUST present it and get approval.

## Process

### 1. Explore Project Context
- Check files, docs, recent commits
- Assess scope — if the request describes multiple independent subsystems, flag it immediately
- If too large for a single spec, decompose into sub-projects first

### 2. Ask Clarifying Questions
- One question at a time — don't overwhelm
- Prefer multiple choice when possible
- Focus on: purpose, constraints, success criteria

### 3. Propose 2-3 Approaches
- Present options with trade-offs
- Lead with your recommendation and reasoning
- Be specific about pros/cons

### 4. Present Design
- Scale each section to its complexity (few sentences to ~300 words)
- Ask after each section whether it looks right
- Cover: architecture, components, data flow, error handling, testing
- Be ready to revise

### 5. Design for Isolation and Clarity
- Break into smaller units with one clear purpose each
- Well-defined interfaces, independently testable
- For each unit: what does it do, how do you use it, what does it depend on?
- Smaller well-bounded units are easier to reason about and edit reliably

### 6. Document the Design
- Write validated design as a spec document
- Self-review: scan for placeholders, contradictions, ambiguity, scope creep
- Fix issues inline

### 7. Get Approval Before Implementation
- Present spec to user for review
- Wait for approval before proceeding to implementation planning
- If changes requested, revise and re-review

## Working in Existing Codebases

- Explore current structure before proposing changes
- Follow existing patterns
- Include targeted improvements where existing code has problems affecting the work
- Don't propose unrelated refactoring — stay focused on the current goal

## Key Principles

| Principle | Why |
|-----------|-----|
| One question at a time | Don't overwhelm — each answer informs the next question |
| Multiple choice preferred | Easier to answer, surfaces options user hadn't considered |
| YAGNI ruthlessly | Remove unnecessary features from all designs |
| Explore alternatives | Always propose 2-3 approaches before settling |
| Incremental validation | Present design, get approval before moving on |
| Be flexible | Go back and clarify when something doesn't make sense |
