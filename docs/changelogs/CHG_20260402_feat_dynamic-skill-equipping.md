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
