# Changelog — feature/dynamic-skill-equipping

Branch started: 2026-04-02

## Changes

### Phase 1: Skill Chain DB + Seeding
- Migration 007: `skill_chains` table + `chain_id`/`chain_state` columns on tasks
- 12 default skill chains seeded:
  - Coding: low (4 steps), medium (7 steps), high (9 steps)
  - Bugfix: simple (3 steps), complex (6 steps)
  - Research: quick (2 steps), deep (4 steps)
  - Security audit (4 steps)
  - Operations: deployment (3 steps), incident (4 steps)
  - Trading: analysis (3 steps), execution (3 steps)
- `scripts/seed-skill-chains.py` — seed script (safe to re-run)
- `make seed-chains` command, hooked into `make clean-slate`

### Phase 2: Chain Matching + Phase Skill Loading
- New `db/skill_chains.py` — `match_chain()` (tag + keyword matching), `get_chain_step_skills()`, `load_skills_by_names()`
- Modified `AgentConfig.get_skills_for_task()` — merges static (global + equipped) + chain phase skills with deduplication
- Token budget enforcement (9000 tokens max, trims chain skills when over)
- Modified heartbeat `_trigger_task_pickup()` — loads dynamic skills before triggering agent loop
- Added `tags` to pending task query
- Static skills as fallback when no chain matches or dynamic loading fails
- Tested: task with `research` tag → matched `research_quick` chain → loaded `research_methodology` skill

### Phase 3: Chain State Tracking + Auto-Advancement
- `set_task_chain_state()` — sets initial chain_state on task when chain is matched
- `advance_chain_phase()` — advances chain to next step, updates chain_state on task
- Heartbeat sets chain_state when task is first picked up
- `research_store` hook — auto-advances chain when PROP:/SPEC:/DESIGN:/VERIFY: documents are stored
- chain_state stored as JSONB on tasks: current_phase, step_index, completed_phases, active_skills, chain_name
- Tested: task TEST-001 → chain_state set with research_quick, phase=research, active_skills=["research_methodology"]
