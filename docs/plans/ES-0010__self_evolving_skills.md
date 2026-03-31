# ES-0010 — Self-Evolving Skills

## Status: COMPLETE (Phase 1-3), Phase 4-6 deferred pending observation

## Problem / Pain Points

Skills are static — manually written, imported once, never updated. When tools change, APIs break, or agents discover better patterns, skills become stale. Agents can't learn from their own experience.

- No feedback loop: agents execute skills but never improve them
- Broken skills stay broken until a human notices and fixes them
- Agents discover useful patterns during tasks but don't capture them
- No quality tracking per skill — no visibility into which skills actually help
- No skill versioning — changes are destructive, no rollback

## Inspiration

Based on patterns from [OpenSpace](https://github.com/HKUDS/OpenSpace) — a self-evolving agent framework that demonstrates 46% token reduction and 4.2x higher task earnings through autonomous skill evolution.

## Suggested Solution

Add three self-improvement mechanisms to inotagent's existing skill system, building on what we already have (DB-driven skills, `skill_create` tool, `self_improvement` skill, heartbeat scheduler).

### Three Evolution Mechanisms

#### FIX — In-Place Repair
Repairs broken/outdated instructions in existing skills.
- **Trigger:** Post-execution analysis detects failure patterns; tool error rates spike
- **Scope:** Same skill, new version
- **Example:** "CoinGecko API changed response format — update parsing instructions"

#### DERIVED — Enhancement
Creates enhanced or specialized versions from parent skills.
- **Trigger:** Successful execution reveals optimization opportunities
- **Scope:** New skill derived from parent(s)
- **Example:** "Merge market_intelligence + trading_analysis into crypto_daily_brief workflow"

#### CAPTURED — Pattern Extraction
Captures novel reusable patterns from successful executions.
- **Trigger:** Agent discovers a workflow worth keeping during task execution
- **Scope:** Brand-new skill with no parent
- **Example:** "Agent figured out a reliable 3-step API retry pattern — capture as skill"

### Architecture Overview

```
Task Execution
    ↓
[Agent executes with skill guidance]
    ↓
[Post-Execution Analysis] ← Trigger 1
    ├─ What worked? What failed?
    ├─ Which skills helped? Which didn't?
    └─ Any patterns worth capturing?
    ↓
[Evolution Suggestions]
    ├─ FIX: skill X has outdated API call
    ├─ DERIVED: combine skill A + B for common workflow
    └─ CAPTURED: novel retry pattern discovered
    ↓
[Skill Evolver] (delegate sub-agent)
    ├─ Read current skill content
    ├─ Apply fix/derive/capture
    ├─ Validate new skill
    └─ Save with version lineage
    ↓
[Updated Skill Library]
```

## Key Decisions

1. **Scope:** Phase 1-3 first (metrics + versioning + analysis), review before Phase 4-6
2. **Analysis trigger:** Extends the existing `memory_and_improvement` daily review skill (Mode 3) rather than creating a separate analysis step — the daily review already gathers data and identifies patterns
3. **Approval flow:** All evolution proposals (FIX, DERIVED, CAPTURED) require human approval — agents propose, humans approve via Admin UI or CLI
4. **DB approach:** New companion tables (`skill_metrics`, `skill_versions`, `skill_evolution_proposals`) rather than altering existing tables — cleaner and more scalable

## Implementation Phases

### Phase 1: Skill Quality Tracking

New companion table `skill_metrics` — tracks per-agent, per-skill usage:

```sql
CREATE TABLE skill_metrics (
    skill_id INT NOT NULL REFERENCES skills(id),
    agent_name VARCHAR(64) NOT NULL,
    times_selected INT DEFAULT 0,       -- skill was in system prompt
    times_applied INT DEFAULT 0,        -- agent actually used the skill
    times_completed INT DEFAULT 0,      -- task completed with skill
    times_fallback INT DEFAULT 0,       -- skill selected but not helpful
    last_applied_at TIMESTAMPTZ,
    UNIQUE (skill_id, agent_name)
);
```

Computed rates (query-time, not stored):
- `applied_rate` = times_applied / times_selected
- `completion_rate` = times_completed / times_applied
- `effective_rate` = times_completed / times_selected
- `fallback_rate` = times_fallback / times_selected

Update counters during task execution in `loop.py`.

### Phase 2: Skill Versioning & Lineage

New companion table `skill_versions` — immutable version history:

```sql
CREATE TABLE skill_versions (
    id BIGSERIAL PRIMARY KEY,
    skill_id INT NOT NULL REFERENCES skills(id),
    version INT NOT NULL DEFAULT 1,
    origin VARCHAR(16) NOT NULL DEFAULT 'imported',
        -- imported, fixed, derived, captured
    parent_version_ids BIGINT[],        -- lineage: parent version(s)
    generation INT NOT NULL DEFAULT 0,  -- distance from original
    change_summary TEXT,                -- LLM-generated description
    content_snapshot TEXT NOT NULL,      -- full skill content at this version
    is_active BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(64),
    UNIQUE (skill_id, version)
);
```

On migration, seeds initial v1 for all existing skills with `origin='imported'`.

### Phase 3: Evolution Proposals (Human Approval)

New table `skill_evolution_proposals` — agents propose, humans approve:

```sql
CREATE TABLE skill_evolution_proposals (
    id BIGSERIAL PRIMARY KEY,
    skill_id INT REFERENCES skills(id),         -- NULL for CAPTURED (new skill)
    evolution_type VARCHAR(16) NOT NULL,         -- fix, derived, captured
    proposed_by VARCHAR(64) NOT NULL,            -- agent name
    status VARCHAR(16) DEFAULT 'pending',        -- pending, approved, rejected, applied
    direction TEXT NOT NULL,                      -- what to change and why
    proposed_content TEXT,                        -- full proposed skill content
    proposed_name VARCHAR(128),                  -- for captured: new skill name
    proposed_description TEXT,
    proposed_tags TEXT[],
    source_task_key VARCHAR(16),                 -- task that triggered this
    review_notes TEXT,                           -- human reviewer notes
    reviewed_by VARCHAR(64),
    reviewed_at TIMESTAMPTZ
);
```

**Agent workflow (extends daily review Mode 3 Phase 4):**
1. Daily review identifies pattern worth formalizing
2. Agent creates evolution proposal via new `skill_propose` tool
3. Proposal saved as `pending` in `skill_evolution_proposals`
4. Human reviews in Admin UI → approve/reject
5. On approve: new `skill_versions` record created, skill content updated

**No auto-apply** — all proposals require human approval.

### Phase 3b: Extend Daily Review for Evolution

Update `0__memory_and_improvement.md` Mode 3 Phase 4 to include evolution proposals:

**Current behavior:** Agent uses `skill_create` to create new skills directly.
**New behavior:** Agent uses `skill_propose` tool to submit proposals for human review.

The daily review already:
1. Gathers completed tasks and research
2. Evaluates quality and efficiency
3. Identifies patterns (repeated tools, corrections, gaps)
4. Formalizes improvements

We add to Phase 4:
```
For patterns worth preserving, submit evolution proposals:

FIX — if a skill had outdated/wrong instructions:
  skill_propose(type="fix", skill_name="<name>", direction="<what to fix>", proposed_content="<fixed content>")

DERIVED — if multiple skills were combined effectively:
  skill_propose(type="derived", skill_name="<name>", direction="<what to combine>", proposed_content="<combined content>")

CAPTURED — if a novel reusable pattern was discovered:
  skill_propose(type="captured", proposed_name="<name>", direction="<what pattern>", proposed_content="<new skill>")

All proposals go to human review — do NOT use skill_create directly.
```

### Phase 4: Skill Evolver (DEFERRED — pending observation)

**What it is:** A delegate sub-agent that auto-generates `proposed_content` for evolution proposals, so agents only need to describe what's wrong (direction) without writing the full improved skill.

**Current flow (Phase 1-3):**
```
Agent notices pattern → writes full proposed_content → skill_propose() → human reviews
```

**Phase 4 flow:**
```
Agent notices pattern → skill_propose(direction="what's wrong") →
  Evolver sub-agent reads current skill + recent history →
  generates polished proposed_content → human reviews
```

**Implementation sketch:**
```python
# In heartbeat — periodic check for proposals needing content generation
async def _check_pending_evolutions(self):
    proposals = await get_proposals(status="pending", has_content=False)
    for proposal in proposals:
        current_skill = await get_skill(proposal.skill_id)
        recent_history = await get_recent_conversations_with_skill(proposal.skill_id, limit=5)

        evolved_content = await delegate(
            skill="skill_create",
            prompt=f"""Evolve this skill:
            Current content: {current_skill.content}
            Issue: {proposal.direction}
            Recent usage context: {recent_history}
            Write the complete improved skill content in markdown."""
        )
        await update_proposal(proposal.id, proposed_content=evolved_content)
```

**Example scenarios:**

*Scenario A: Agent writes good content (Phase 4 NOT needed)*
```
ino runs daily review → notices CoinGecko API changed response format →
skill_propose(type="fix", skill_name="trading_analysis",
  direction="CoinGecko API v3.1 changed /ohlc endpoint to return timestamps in ISO format",
  proposed_content="# Trading Analysis\n\n## Market Data\n...full updated skill with ISO parsing...")
→ Human reviews complete content → approves
```
Here ino wrote the full fix. Phase 4 adds no value.

*Scenario B: Agent describes issue but can't write content (Phase 4 IS needed)*
```
robin runs daily review → notices 3 tasks failed because shell scripts didn't handle network timeouts →
skill_propose(type="captured", proposed_name="network_resilience",
  direction="Multiple tasks failed due to network timeouts in curl/requests calls. Need retry pattern.")
→ proposed_content is empty or vague
→ WITHOUT Phase 4: human has to write the skill content themselves
→ WITH Phase 4: evolver reads robin's recent failures, generates comprehensive retry skill
```

*Scenario C: Metric-triggered evolution (requires Phase 4 + 5)*
```
skill_metrics shows: trading_operations fallback_rate = 0.65 (selected 20 times, fell back 13 times)
→ Phase 5 auto-creates proposal: type="fix", direction="High fallback rate (65%) — skill not applicable"
→ Phase 4 evolver reads the 13 fallback conversations, identifies WHY the skill wasn't helpful
→ Generates targeted fix that addresses actual gaps
→ Human reviews
```

**Why we defer:**

| Argument | Details |
|----------|---------|
| **Observe first** | We don't know yet if agents write good proposals or vague ones. If proposals come with good content, Phase 4 is unnecessary overhead. |
| **Cost concern** | Each evolver call = full delegate LLM call. With 6 proposals/week = 6 extra LLM calls. Not expensive, but worth validating the need first. |
| **Current flow works** | Phase 1-3 already provides the full proposal → review → apply pipeline. Agents CAN write proposed_content themselves. |
| **Phase 5 dependency** | The most compelling use case (metric-triggered evolution) requires Phase 5 first. Without metric triggers, the evolver only helps lazy proposals. |
| **Complexity** | Adds heartbeat logic, proposal state management (pending_content vs pending_review), and error handling for failed generations. |

**When to implement Phase 4:**
- After 2-4 weeks of Phase 1-3 in production
- If >50% of proposals have empty/vague proposed_content → agents need help writing content
- If Phase 5 (metric triggers) is prioritized → evolver is required for auto-generated proposals
- If human reviewer feedback indicates proposal quality is consistently poor

**Pros of implementing:**
- Agents can submit lightweight proposals (just direction, no full content)
- Higher quality evolved skills (focused sub-agent with full context + execution history)
- Enables fully autonomous evolution pipeline (Phase 5 triggers → Phase 4 generates → human reviews)
- Reduces burden on agents during daily review (propose direction, not content)

**Cons of implementing now:**
- Extra LLM calls (cost, latency)
- More complex heartbeat logic and state management
- May be unnecessary if agents write good proposals
- Adds another failure point (evolver generates bad content → wasted human review time)

### Phase 5: Metric-Based Evolution Trigger

Add to heartbeat — periodically check skill health:

```python
# Run weekly or when idle
async def check_skill_health():
    """Find underperforming skills and trigger evolution."""
    skills = await get_skill_metrics()
    for skill in skills:
        if skill.fallback_rate > 0.5:  # Used but not helpful >50% of the time
            await trigger_evolution("FIX", skill, "High fallback rate")
        if skill.applied_rate < 0.1 and skill.times_selected > 10:
            await trigger_evolution("FIX", skill, "Selected but rarely applied")
```

### Phase 6: Admin UI — Skill Evolution Dashboard (DEFERRED — pending data)

Add skill evolution visibility to the Admin UI. Two possible locations:

**Option A: Extend existing Skills page (`/skills`)**
- Add metrics badge per skill (completion rate, fallback rate)
- Add "Versions" tab in skill detail
- Add "Proposals" filter/tab

**Option B: New dedicated page (`/skill-evolution`)**
- Pending proposals queue (approve/reject with one click)
- Skill health dashboard (metrics heatmap — green/yellow/red per skill)
- Version lineage tree (DAG visualization per skill family)
- Evolution log (timeline of all changes)

**What each view provides:**

| View | Purpose | Example |
|------|---------|---------|
| **Proposals Queue** | Human reviews pending proposals | "ino proposes fixing trading_analysis — RSI divergence missing. [Approve] [Reject]" |
| **Skill Metrics** | Identify underperforming skills | "trading_operations: 65% fallback rate, selected 20 times, helpful only 7 times" |
| **Version History** | Track how a skill evolved | "v1 (imported) → v2 (fixed: API format change) → v3 (derived: merged with market_intel)" |
| **Evolution Timeline** | Audit trail of all changes | "Mar 31: ino captured api_retry_pattern. Apr 2: robin fixed trading_ops. Apr 5: rejected ino's merge proposal." |

**Why we defer:**

| Argument | Details |
|----------|---------|
| **No data yet** | Metrics table is empty (just started tracking). Need 1-2 weeks of data before a dashboard is useful. |
| **API already works** | All data is accessible via API endpoints — `curl` or Postman for now. |
| **Proposal volume is low** | Agents submit proposals during daily review (~1/day). A queue UI isn't critical for 1-2 proposals/week. |
| **Gamified office is the primary UI** | The office view is where users spend time. Proposals could be surfaced there instead (notification bubble, inbox in agent panel). |
| **Prioritize ES-0012** | Robin trading toolkit has higher business impact than a dashboard for skill evolution. |

**When to implement Phase 6:**
- After 2+ weeks of metric data has accumulated
- If proposal volume increases (Phase 4/5 auto-generates more proposals)
- If human reviewer finds curl/API approval tedious
- After ES-0012 (trading toolkit) is done

**Alternative: Lightweight proposal review in office panel**

Instead of a full Admin UI page, add a "Proposals" tab to the Agent Panel in the gamified office:
```
Agent Panel → new tab "Evolution"
  - List of pending proposals by this agent
  - One-click approve/reject
  - Shows current skill content vs proposed content (diff view)
```

This is simpler than a full dashboard and lives where the user already interacts with agents. Could be done as a Phase 6a (quick win) before the full dashboard (Phase 6b).

**Estimated effort:**
- Phase 6a (agent panel proposals tab): 1 day
- Phase 6b (full admin dashboard): 3-4 days

## Implementation Steps (Phase 1-3)

- [x] Phase 1: Create `skill_metrics` companion table (migration 006)
- [x] Phase 1: Add metric increment logic to `loop.py`
- [x] Phase 1: Create API endpoint for metrics (`/api/skills/[id]/metrics`)
- [x] Phase 2: Create `skill_versions` companion table (migration 006)
- [x] Phase 2: Seed initial v1 for all existing skills on migration
- [x] Phase 2: Create API endpoints for versions (`/api/skills/[id]/versions`)
- [x] Phase 3: Create `skill_evolution_proposals` table (migration 006)
- [x] Phase 3: Create `skill_propose` tool in inotagent (tool #21)
- [x] Phase 3: Create API endpoints for proposals (`/api/skill-proposals`)
- [x] Phase 3b: Update `memory_and_improvement` skill to use `skill_propose` instead of `skill_create`
- [x] Phase 3b: Create proposal approval API (PATCH status)
- [x] Security: Fix JS `in` operator bug in approval API (fix/derived proposals silently failing)

### Deferred (Phase 4-6, pending review)

- [ ] Phase 4: Skill evolver delegate agent (auto-generates proposed content)
- [ ] Phase 4: Apply approved proposals → create new skill version + update skill content
- [ ] Phase 5: Metric-based trigger in heartbeat (detect underperforming skills)
- [ ] Phase 6: Admin UI — skill evolution dashboard (proposals, versions, metrics)

## Guardrails & Safety

| Guardrail | Purpose |
|-----------|---------|
| Human approval required | ALL proposals (FIX, DERIVED, CAPTURED) need human review |
| Rollback capability | Old versions preserved (`is_active=FALSE`), one-click revert |
| Max evolution frequency | No more than 3 evolutions per skill per day |
| Anti-loop detection | Prevent FIX → FIX → FIX cycles on the same skill |
| Dangerous pattern blocking | Block skills that contain credential access, prompt injection |
| Evolution audit log | All changes tracked with timestamp, trigger, and diff |

## Dependencies

- Existing: `skills` + `agent_skills` tables, `skill_create` tool, `delegate` tool, `self_improvement` skill
- New: DB migration for metrics + versioning columns
- No new external dependencies

## Success Criteria

- Skills autonomously improve based on execution experience
- Quality metrics visible in Admin UI
- Failed skills get fixed without human intervention
- Novel patterns captured as reusable skills
- Full lineage tracking — can trace any skill back to its origin
- No runaway evolution (budget + anti-loop guardrails)

## References

- [OpenSpace](https://github.com/HKUDS/OpenSpace) — Self-evolving agent framework (FIX/DERIVED/CAPTURED pattern)
- ES-0009 — Proactive Agent Behavior (prerequisite — idle agents trigger analysis)
- Existing `self_improvement` skill — memory-backed learning from feedback
