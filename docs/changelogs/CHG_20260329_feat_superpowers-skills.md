# Changelog — feature/superpowers-skills

Branch started: 2026-03-29

## Summary

Extracted 8 workflow skills from [superpowers](https://github.com/obra/superpowers) (obra/superpowers) — a composable AI agent workflow framework. Skills adapted for inotagent format with proper YAML frontmatter, tags, and source attribution.

## New Skills (81 → 89)

| Skill | Tags | Description |
|-------|------|-------------|
| `systematic_debugging` | debugging, troubleshooting | 4-phase root cause analysis with defense in depth |
| `brainstorming` | planning, design | Design-first workflow — explore, propose, approve before implementation |
| `test_driven_development` | testing, tdd | RED-GREEN-REFACTOR enforcement with anti-patterns guide |
| `writing_plans` | planning, development | Break specs into bite-sized tasks with complete code and TDD steps |
| `subagent_driven_development` | development, delegation | Fresh subagent per task with two-stage review (spec + quality) |
| `parallel_agent_dispatch` | delegation, parallelism | Dispatch concurrent agents for independent problem domains |
| `verification_before_completion` | quality, verification | Evidence before claims — run verification before any completion claims |
| `finishing_dev_branch` | git, workflow | Guide branch completion — verify, merge/PR/keep/discard, cleanup |

## Other Changes

- Added superpowers attribution to README.md Acknowledgements section
- Cloned superpowers repo to `resources/superpowers/` for reference
