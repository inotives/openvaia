# Changelog — feature/spec-driven-skills

Branch started: 2026-04-01

## Summary

Extracted 4 spec-driven development skills from [OpenSpec](https://github.com/Fission-AI/OpenSpec) by Fission AI. Skills teach agents structured planning before implementation: Proposal → Spec → Design → Verification.

## New Skills (98 → 102)

| Skill | Tag Prefix | Required Tag | Description |
|-------|-----------|-------------|-------------|
| `spec_driven_proposal` | `PROP:` | `proposal` | Structured change proposal — motivation, scope, success criteria, impact, rollback plan |
| `requirement_specification` | `SPEC:` | `spec` | RFC 2119 requirements with Given/When/Then scenarios |
| `technical_design_doc` | `DESIGN:` | `design` | Architecture, components, data flow, API contracts, alternatives, edge cases |
| `spec_verification` | `VERIFY:` | `verification` | Verify implementation against spec — evidence-based report per requirement |

## Document Tagging Convention

All planning documents stored via `research_store` with standardized prefix and tag:
- `PROP: [name]` + tag `proposal`
- `SPEC: [name]` + tag `spec`
- `DESIGN: [name]` + tag `design`
- `VERIFY: [name]` + tag `verification`

Searchable via: `research_search(tags=["proposal"])`, etc.

### Global Workflow Orchestration Skill
- Created `0__development_workflow.md` — routes agents to correct workflow based on task complexity
- Covers: quick fix, small/medium/large features, research, operations
- Defines human approval gates, document storage conventions, and scaling guidance

### Plans
- Updated ES-0013 with document trail, scaling by complexity, and tagging convention
- Created ES-0014 (Dynamic Skill Equipping) — skill chains with phase-based loading, chain_state tracking, human approval gates, backward compatibility with static skills

## Other Changes

- Added OpenSpec attribution to README.md
- Updated skill counts across all docs: 98 → 103 (5 global + 98 non-global)
- Updated project_summary and project_details with ES-0013 + ES-0014
