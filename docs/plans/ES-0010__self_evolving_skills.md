# ES-0010 — Self-Evolving Skills

## Status: DRAFT

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

## Implementation Phases

### Phase 1: Skill Quality Tracking

Add metrics to the existing `skills` or `agent_skills` table:

```sql
ALTER TABLE agent_skills ADD COLUMN times_selected INT DEFAULT 0;
ALTER TABLE agent_skills ADD COLUMN times_applied INT DEFAULT 0;
ALTER TABLE agent_skills ADD COLUMN times_completed INT DEFAULT 0;
ALTER TABLE agent_skills ADD COLUMN times_fallback INT DEFAULT 0;
ALTER TABLE agent_skills ADD COLUMN last_applied_at TIMESTAMPTZ;
```

Computed rates:
- `applied_rate` = times_applied / times_selected
- `completion_rate` = times_completed / times_applied
- `effective_rate` = times_completed / times_selected
- `fallback_rate` = times_fallback / times_selected

Update counters during task execution in `loop.py`.

### Phase 2: Skill Versioning & Lineage

Add version tracking to skills:

```sql
ALTER TABLE skills ADD COLUMN version INT DEFAULT 1;
ALTER TABLE skills ADD COLUMN origin VARCHAR(16) DEFAULT 'imported';
  -- imported, fixed, derived, captured
ALTER TABLE skills ADD COLUMN parent_skill_ids INT[];
ALTER TABLE skills ADD COLUMN generation INT DEFAULT 0;
ALTER TABLE skills ADD COLUMN change_summary TEXT;
ALTER TABLE skills ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
```

- Multiple versions of the same skill can exist (only `is_active=TRUE` is used)
- `parent_skill_ids` tracks lineage for DERIVED skills
- `generation` tracks distance from original (0 = imported, 1 = first evolution, etc.)
- `change_summary` is LLM-generated description of what changed

### Phase 3: Post-Execution Analysis

After each task completion, run an analysis step:

```python
# In heartbeat or loop.py, after task completes
async def analyze_execution(agent, task, conversation_id):
    """Analyze completed task execution for skill evolution opportunities."""
    # Load conversation history
    history = await load_history(conversation_id)

    # Build analysis prompt
    prompt = f"""Analyze this task execution:
    Task: {task.title}
    Status: {task.status}
    Skills used: {agent.config._skill_names}

    Review the conversation and identify:
    1. Which skills were helpful? Which weren't?
    2. Did any skill have outdated/wrong instructions? (→ FIX)
    3. Were multiple skills used together that could be combined? (→ DERIVED)
    4. Did you discover a novel pattern worth capturing? (→ CAPTURED)

    Return structured suggestions or 'no evolution needed'.
    """

    # Run as delegate sub-agent (lightweight, no tools)
    result = await delegate(skill="self_improvement", prompt=prompt)
    return parse_evolution_suggestions(result)
```

Frequency: Run after every task completion where `status = 'done'`.

### Phase 4: Skill Evolver

A delegate sub-agent that applies evolution suggestions:

```python
async def evolve_skill(suggestion):
    if suggestion.type == "FIX":
        # Read current skill, apply fix, save new version
        current = await get_skill(suggestion.skill_id)
        new_content = await delegate(
            skill="skill_create",
            prompt=f"Fix this skill:\n{current.content}\n\nIssue: {suggestion.direction}"
        )
        await save_skill_version(current, new_content, origin="fixed")

    elif suggestion.type == "DERIVED":
        # Read parent skills, create combined version
        parents = [await get_skill(id) for id in suggestion.parent_ids]
        new_content = await delegate(
            skill="skill_create",
            prompt=f"Create a new skill combining:\n{format_parents(parents)}\n\nGoal: {suggestion.direction}"
        )
        await create_derived_skill(parents, new_content)

    elif suggestion.type == "CAPTURED":
        # Create brand-new skill from pattern
        new_content = await delegate(
            skill="skill_create",
            prompt=f"Create a new skill capturing this pattern:\n{suggestion.direction}"
        )
        await create_captured_skill(new_content)
```

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

### Phase 6: Admin UI — Skill Evolution Dashboard

Add to the existing Skills page:
- Skill lineage visualization (version history)
- Quality metrics per skill (applied/completion/fallback rates)
- Evolution log (what was fixed/derived/captured and why)
- Manual trigger: "Analyze and evolve this skill"

## Implementation Steps

- [ ] Phase 1: Add quality metric columns to `agent_skills`
- [ ] Phase 1: Update counters in `loop.py` during execution
- [ ] Phase 1: Display metrics in Admin UI Skills page
- [ ] Phase 2: Add versioning columns to `skills` table
- [ ] Phase 2: Migration to support multiple active versions
- [ ] Phase 2: Update `import-skills.py` to set `origin='imported'`
- [ ] Phase 3: Create `post_execution_analysis` function
- [ ] Phase 3: Hook into task completion flow
- [ ] Phase 3: Create `0__execution_analysis.md` global skill
- [ ] Phase 4: Create skill evolver delegate agent
- [ ] Phase 4: Implement FIX/DERIVED/CAPTURED flows
- [ ] Phase 4: Add validation before replacing skills
- [ ] Phase 5: Add metric-based trigger to heartbeat
- [ ] Phase 5: Configure thresholds via `agent_configs`
- [ ] Phase 6: Skill lineage UI in Admin dashboard
- [ ] Phase 6: Evolution log display

## Guardrails & Safety

| Guardrail | Purpose |
|-----------|---------|
| Validation before replacement | New skill version must pass syntax/format check |
| Human approval for major changes | DERIVED and CAPTURED skills flagged for review |
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
