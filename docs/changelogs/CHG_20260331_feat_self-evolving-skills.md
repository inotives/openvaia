# Changelog — feature/self-evolving-skills

Branch started: 2026-03-31

## Changes

### Phase 1-2: DB Schema (Migration 006)
- New `skill_metrics` table — per-agent, per-skill quality tracking (selected, applied, completed, fallback counts)
- New `skill_versions` table — immutable version history with origin (imported/fixed/derived/captured), lineage, generation tracking
- New `skill_evolution_proposals` table — agents propose, humans approve (pending/approved/rejected/applied)
- Seeded initial v1 for all 98 existing skills

### Phase 3: skill_propose Tool
- New `skill_propose` tool (#21) in inotagent — agents submit evolution proposals
- Supports 3 types: fix (repair broken skill), derived (enhance/combine), captured (new pattern)
- All proposals saved as `pending` — require human approval
- Validates skill exists for fix/derived, requires proposed_name for captured

### Phase 3: API Endpoints
- `GET /api/skill-proposals` — list proposals (filterable by status)
- `GET /api/skill-proposals/[id]` — get single proposal with current skill content
- `PATCH /api/skill-proposals/[id]` — approve/reject proposal
  - On approve: creates new skill_version, updates skill content, marks as applied
  - On reject: saves review notes

### Phase 3b: Updated Daily Review Skill
- Updated `memory_and_improvement` Mode 3 Phase 4 to use `skill_propose` instead of `skill_create`
- Added examples for FIX, DERIVED, CAPTURED proposal types

### Testing
- Tested CAPTURED flow: ino proposed `api_retry_pattern` → approved → new skill + version created
- Tested FIX flow: ino proposed fixing `trading_analysis` → saved as pending
- Tested rejection: human rejected FIX proposal with review notes

### Phase 1: Skill Metrics Tracking
- Added `_update_skill_metrics()` to `loop.py` — increments `times_selected` and `times_completed` for all equipped skills after each conversation
- Upserts into `skill_metrics` table (creates row if first time, increments if exists)

### API Endpoints for Metrics & Versions
- `GET /api/skills/[id]/metrics` — per-agent metrics + totals (effective_rate, fallback_rate)
- `GET /api/skills/[id]/versions` — version history with lineage (origin, generation, change_summary)

### Security Fix
- Fixed `in` operator bug in proposal approval API — `p.evolution_type in ["fix", "derived"]` always returned false (JS `in` checks array keys, not values). Changed to `.includes()`. Without this fix, fix/derived proposals would silently fail to apply skill changes despite status showing "applied".
- Verified: all `/api/skill-proposals/*` endpoints are behind NextAuth middleware (no unauthenticated access)

### ES-0010 Plan Updates
- Updated Phase 4 (Skill Evolver) with deferral analysis: example scenarios, pros/cons, when to implement
- Updated Phase 6 (Admin UI) with deferral analysis: lightweight alternative (agent panel tab), effort estimates
