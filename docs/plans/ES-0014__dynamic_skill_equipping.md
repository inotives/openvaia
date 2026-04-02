# ES-0014 — Dynamic Skill Equipping

## Status: DRAFT

## Problem

Skills are currently **statically equipped** — an agent's skills are set at boot time and refreshed every heartbeat (60s). The agent always has the same skills regardless of what task it's working on.

Issues with static equipping:
- **Context window bloat** — all equipped skills injected into system prompt even when irrelevant
- **No task awareness** — agent doing research gets coding skills injected; agent doing coding gets research skills
- **Manual skill management** — human must manually equip/unequip skills via Admin UI
- **One-size-fits-all** — same skill set for a quick fix and a large feature

## Suggested Solution

Replace static skill equipping with **dynamic, context-aware skill selection** that loads relevant skills based on the current task.

### How It Works

```
Input arrives (chat message or task)
    ↓
[Is this a task?]
    ├─ YES (has tags, from task system) → Match to skill chain
    └─ NO (ad-hoc chat/conversation) → Use static equipped skills
         ↓
         [Contains task keywords? "research", "task", "mission", "design", etc.]
         ├─ YES → Convert to task, then match to skill chain
         └─ NO → Normal conversation with static skills
    ↓
[Skill Chain Matched]
    ↓
Load skills for CURRENT phase only (not entire chain)
    ↓
Agent executes with focused, relevant context
    ↓
Phase completes → advance chain → load next phase's skills
    ↓
After task: update skill_metrics (which skills were useful)
```

### Chat vs Task Handling

**Ad-hoc chat (Discord, Slack, web):** Uses the agent's statically equipped skills. Normal conversational behavior — no chain.

**Task-triggering keywords in chat:** When a chat message contains keywords like "research", "task", "mission", "design", "implement", "build", "fix", "debug" — the agent converts it to a formal task first, then the chain system activates.

**Formal tasks (heartbeat, task_create):** Always matched to a skill chain based on tags.

### Skill Selection Strategy

**Layer 1: Global skills (always loaded)**
- `communication`, `memory_and_improvement`, `resource_first_research`, `idle_behavior`, `development_workflow`
- These are always relevant regardless of task type

**Layer 2: Skill Chains (task-type + complexity driven)**

Instead of flat skill lists, define **ordered chains** — sequences of skills the agent follows step-by-step. The agent only loads skills for the current phase, not the entire chain at once.

#### Coding Task Chains

**Low complexity** (quick fix, small bug, config change):
```
writing_plans → test_driven_development → verification_before_completion → finishing_dev_branch
```

**Medium complexity** (new endpoint, UI page, integration):
```
spec_driven_proposal → requirement_specification → writing_plans
  → test_driven_development → pre_landing_review → spec_verification
  → ship_workflow
```

**High complexity** (new system, multi-component, architecture change):
```
brainstorming → spec_driven_proposal → requirement_specification
  → technical_design_doc → writing_plans → subagent_driven_development
  → [per subtask: test_driven_development → pre_landing_review]
  → spec_verification → ship_workflow → finishing_dev_branch
```

#### Bugfix Chains

**Simple bug:**
```
systematic_debugging → test_driven_development → verification_before_completion
```

**Complex bug (3+ failed fix attempts):**
```
systematic_debugging → brainstorming (rethink architecture)
  → spec_driven_proposal → writing_plans → test_driven_development
  → spec_verification
```

#### Research Chains

**Quick research:**
```
resource_first_research → report_format
```

**Deep research:**
```
resource_first_research → research_methodology → literature_review
  → report_format → market_intelligence
```

#### Security Chains

**Security audit:**
```
security_audit → vulnerability_scanning → access_audit → report_format
```

#### Operations Chains

**Deployment:**
```
ship_workflow → canary_monitoring → performance_benchmark
```

**Incident:**
```
incident_response → systematic_debugging → log_analysis
  → deployment_monitoring
```

#### Trading Chains (robin-specific)

**Market analysis:**
```
trading_analysis → market_intelligence → report_format
```

**Trade execution:**
```
trading_analysis → trading_operations → portfolio_rebalancing
  → risk_assessment
```

### How Chains Work at Runtime

```
1. Task arrives with tags/title
2. System matches to a chain (tag mapping + keyword fallback)
3. Agent starts at step 1 of the chain
4. Only skills for the CURRENT step are loaded into system prompt
5. When step completes → unload current skill, load next step's skill
6. Agent progresses through the chain until done
```

**Key insight:** At any given time, agent only has 1-3 task-specific skills loaded (current phase), not the entire chain. This keeps context focused and token-efficient.

### Chain Selection Logic

**Priority order for matching:**
1. **Explicit task tags** — `tags: ["feature", "high"]` → High complexity coding chain
2. **Task type tags** — `tags: ["bugfix"]` → Bugfix chain
3. **Title keyword matching** — "debug", "fix" → Bugfix chain; "research", "analyze" → Research chain
4. **Agent role fallback** — ino defaults to research chain, robin defaults to coding chain
5. **Complexity inference** — if no complexity tag, estimate from task description length and scope

| Tag Combo | Chain |
|-----------|-------|
| `feature` + `low` | Coding: Low |
| `feature` + `medium` | Coding: Medium |
| `feature` + `high` or `large` | Coding: High |
| `bugfix` | Bugfix: Simple |
| `bugfix` + `complex` | Bugfix: Complex |
| `research` | Research: Quick |
| `research` + `deep` | Research: Deep |
| `security` | Security |
| `deploy` or `ship` | Operations: Deployment |
| `incident` | Operations: Incident |
| `trading` + `analysis` | Trading: Analysis |
| `trading` + `execution` | Trading: Execution |

**Layer 3: Agent-specific skills (always loaded for that agent)**
- ino: `task_workflow_ino`
- robin: `task_workflow_robin`

**Layer 4: Keyword-based semantic matching (fallback)**
If no chain matches, use BM25/keyword search on task title + description against skill names and descriptions. Select top 5 most relevant skills.

### Token Budget

Current problem: all equipped skills (~15-20) always in system prompt = ~5000-8000 tokens wasted on irrelevant skills.

With skill chains:
- Global skills: ~2500 tokens (always)
- Current chain step: ~1000-2000 tokens (1-3 skills for current phase)
- Agent-specific: ~500 tokens
- Total: ~4000-5000 tokens (focused, relevant, phase-appropriate)

Max skill budget: configurable via `agent_configs` (default: `max_skill_tokens: 9000`)

### Chain Storage

Chains are stored in the DB as JSON in a new `skill_chains` table:

```sql
CREATE TABLE skill_chains (
    id SERIAL PRIMARY KEY,
    name VARCHAR(64) NOT NULL UNIQUE,       -- e.g. 'coding_high'
    description TEXT,
    match_tags TEXT[] NOT NULL,              -- tags that trigger this chain
    match_keywords TEXT[],                   -- title keywords that trigger this chain
    steps JSONB NOT NULL,                    -- ordered array of steps
    -- steps format: [
    --   {"phase": "propose", "skills": ["spec_driven_proposal"], "gate": "human_approval"},
    --   {"phase": "specify", "skills": ["requirement_specification"]},
    --   {"phase": "design", "skills": ["technical_design_doc"], "gate": "human_approval"},
    --   {"phase": "plan", "skills": ["writing_plans"]},
    --   {"phase": "implement", "skills": ["test_driven_development", "subagent_driven_development"]},
    --   {"phase": "verify", "skills": ["spec_verification"]},
    --   {"phase": "ship", "skills": ["ship_workflow", "finishing_dev_branch"]}
    -- ]
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Each step can have:
- `phase` — human-readable name
- `skills` — skills to load for this phase
- `gate` — optional: `human_approval` (pause and ask human before proceeding)

### Chain State on Tasks

Track current chain progress on the task itself (not derived from documents):

```sql
-- Add to tasks table
ALTER TABLE tasks ADD COLUMN chain_id INT REFERENCES skill_chains(id);
ALTER TABLE tasks ADD COLUMN chain_state JSONB;
-- chain_state format:
-- {
--   "current_phase": "implement",
--   "current_step_index": 4,
--   "completed_phases": ["propose", "specify", "design", "plan"],
--   "active_skills": ["test_driven_development"],
--   "started_at": "2026-04-01T10:00:00Z"
-- }
```

This is the source of truth for chain progress — not document detection.
When agent stores a PROP/SPEC/DESIGN/VERIFY document, the chain_state advances automatically.

### Title Standardization

For phase detection to work reliably, document titles MUST match the task:
- Task title: "Add Email Notifications"
- Proposal: `PROP: Add Email Notifications` (exact match with prefix)
- Spec: `SPEC: Add Email Notifications`
- Design: `DESIGN: Add Email Notifications`
- Verification: `VERIFY: Add Email Notifications`

The `research_store` calls should use the task title directly — no paraphrasing.

### Subtask Handling

Subtasks (from `subagent_driven_development`) are **atomic** — each subtask:
- Gets exactly 1 skill loaded (the implementation skill for that step)
- Does NOT inherit the parent's full chain
- Is a single focused unit of work
- Reports back to the parent task when done

Example: high complexity chain reaches "implement" phase → creates 5 subtasks → each subtask gets only `test_driven_development` skill → subtask completes → parent chain advances to "verify" phase.

### Chain Switching

If agent discovers mid-task that complexity was underestimated (e.g., "small bugfix" is actually an architecture issue):

1. Agent stops current task — sets status to `blocked`
2. Agent reports to human: "This is more complex than expected. Recommend upgrading to [chain name]."
3. Human approves → agent re-tags task, re-assigns chain
4. Chain restarts from the appropriate phase (may reuse existing PROP/SPEC if applicable)

**No automatic chain switching** — always involves human decision.

### Backward Compatibility

Static skill equipping continues to work alongside dynamic chains:

| Scenario | Skill Source |
|----------|-------------|
| Formal task with matching chain | Chain phase skills (dynamic) |
| Formal task, no chain match | Statically equipped skills (fallback) |
| Ad-hoc chat conversation | Statically equipped skills |
| Idle/autonomous behavior | Statically equipped skills |

Agents keep their manually equipped skills. Chains ADD focused skills on top for task execution.
Static skills are useful for always-on domain knowledge (e.g., robin always has `trading_operations` for market awareness).

## Implementation Phases

### Phase 1: Skill Chain DB + Seeding

Create `skill_chains` table and seed default chains:

```python
# Migration 007
CREATE TABLE skill_chains (
    id SERIAL PRIMARY KEY,
    name VARCHAR(64) NOT NULL UNIQUE,
    description TEXT,
    match_tags TEXT[] NOT NULL,
    match_keywords TEXT[],
    steps JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Seed script with all chains defined above (coding low/medium/high, bugfix, research, security, operations, trading).

### Phase 2: Chain Matching + Phase Skill Loading

Modify skill loading to be task-aware:

```python
async def get_skills_for_task(agent_config, task):
    # Always loaded
    global_skills = await get_global_skills()
    agent_skills = await get_agent_specific_skills(agent_config.name)

    # Match task to a chain
    chain = await match_chain(task.tags, task.title)
    if chain:
        # Determine current phase (based on task progress / artifacts created)
        current_step = await get_current_chain_step(chain, task)
        phase_skills = await load_skills_by_names(current_step["skills"])
    else:
        # Fallback: keyword search
        phase_skills = await match_skills_by_keywords(task.title, limit=5)

    # Merge, deduplicate, enforce token budget
    all_skills = global_skills + agent_skills + phase_skills
    return trim_to_token_budget(all_skills, max_tokens=6000)
```

### Phase 3: Phase Progression via chain_state

Phase tracking uses `chain_state` on the task (source of truth), not document detection:

```python
async def get_current_chain_step(chain, task):
    state = task.get("chain_state") or {"current_step_index": 0, "completed_phases": []}
    steps = chain["steps"]
    idx = state["current_step_index"]
    return steps[min(idx, len(steps) - 1)]

async def advance_chain_phase(task, completed_phase):
    """Called after agent stores PROP/SPEC/DESIGN/VERIFY document."""
    state = task["chain_state"]
    state["completed_phases"].append(completed_phase)
    state["current_step_index"] += 1

    chain = await get_chain(task["chain_id"])
    next_step = chain["steps"][state["current_step_index"]]
    state["current_phase"] = next_step["phase"]
    state["active_skills"] = next_step["skills"]

    await update_task_chain_state(task["key"], state)
```

**Advancement triggers:**
- Agent calls `research_store` with `PROP:` prefix → advance past "propose" phase
- Agent calls `research_store` with `SPEC:` prefix → advance past "specify" phase
- Agent calls `research_store` with `DESIGN:` prefix → advance past "design" phase
- Agent calls `task_create` for subtasks → advance past "plan" phase
- Agent calls `research_store` with `VERIFY:` prefix → advance past "verify" phase

These triggers are hooked into the `research_store` and `task_create` tool handlers — when a document with a known prefix is stored, chain_state auto-advances.

### Phase 4: Human Approval Gates

When a chain step has `"gate": "human_approval"`:
1. Agent completes the document (PROP, SPEC, DESIGN)
2. Agent pauses and asks human: "Proposal ready for review. Approve to proceed?"
3. Agent waits for human response before loading next phase's skills
4. If rejected → agent revises, stays on same phase

### Phase 5: Learning from Metrics

Use `skill_metrics` (ES-0010) to improve chain effectiveness:
- Track which chains lead to successful task completion
- Adjust chain skill ordering based on what agents actually use
- Suggest new chains based on frequently co-selected skills

### Phase 6: Agent Self-Select (Mid-Conversation)

New tool for on-demand skill loading:
```
skill_equip(name="security_audit")
→ Loads skill content into current conversation context
→ Only for current conversation (not persistent)
→ Token budget still enforced
```

Use case: agent is mid-implementation and encounters a security concern — loads security_audit skill without restarting.

## Implementation Steps

- [ ] Phase 1: Create `skill_chains` table (migration 007)
- [ ] Phase 1: Add `chain_id` + `chain_state` columns to tasks table (migration 007)
- [ ] Phase 1: Create `scripts/seed-skill-chains.py` with all default chains
- [ ] Phase 1: Add `make seed-chains` command, hook into `make clean-slate`
- [ ] Phase 2: Add `match_chain()` function — tag matching + keyword fallback
- [ ] Phase 2: Modify skill loading to be task-aware (`get_skills_for_task()`)
- [ ] Phase 2: Load phase-specific skills when task is picked up via heartbeat
- [ ] Phase 2: Static skills as fallback for chat conversations and unmatched tasks
- [ ] Phase 2: Implement token budget enforcement (max 9000 tokens)
- [ ] Phase 2: Add chat keyword detection for task conversion
- [ ] Phase 3: Implement `chain_state` tracking on tasks
- [ ] Phase 3: Hook `research_store` tool — auto-advance chain on PROP/SPEC/DESIGN/VERIFY
- [ ] Phase 3: Hook `task_create` tool — auto-advance chain on subtask creation
- [ ] Phase 3: Subtask gets single atomic skill (not parent chain)
- [ ] Phase 4: Human approval gate handling (pause + ask + wait at gate steps)
- [ ] Phase 4: Chain switch flow (stop → re-tag → restart from appropriate phase)
- [ ] Phase 5: Record active skills + chain + phase in assistant response metadata
- [ ] Phase 5: Integrate `skill_metrics` for chain effectiveness tracking
- [ ] Phase 6: Add `skill_equip` tool for mid-conversation skill loading
- [ ] Testing: Unit tests for chain matching, phase detection, advancement
- [ ] Testing: Integration tests for full task → chain → phase → complete flow
- [ ] Testing: Regression tests for static skill equipping backward compatibility

### Skill Usage Recording in Conversation Metadata

Record which skills were active in every assistant response metadata. This enables:
- Daily review can see which skills were used per conversation
- Skill metrics can track `times_applied` more accurately
- Post-execution analysis (ES-0010) knows exactly what skills were in context

**Current state:** Skill names recorded only on the first user message metadata.

**Proposed:** Add `skills` and `chain` fields to every assistant response metadata:

```json
{
  "model": "nvidia-minimax-2.5",
  "input_tokens": 8500,
  "output_tokens": 650,
  "total_tokens": 9150,
  "skills": ["writing_plans", "test_driven_development"],
  "chain": "coding_medium",
  "chain_phase": "implement"
}
```

**Implementation:**
- Modify `_usage_meta()` in `loop.py` to accept and include skill names, chain name, and current phase
- Pass `self.config._skill_names` to every `_usage_meta()` call
- When chain is active, include chain name and current phase

**Benefits for daily review:**
- `memory_and_improvement` Mode 3 can query: "which skills were active when this task was completed?"
- Identify patterns: "every time I used `systematic_debugging`, tasks completed faster"
- Detect unused skills: "skill was loaded but agent never referenced it in output"
- Feed into `skill_propose`: "I never use X skill, maybe it needs a FIX"

## Guardrails

| Guardrail | Purpose |
|-----------|---------|
| Global skills always loaded | Core behaviors never lost |
| Agent-specific skills always loaded | Role identity preserved |
| Static skills still work | Backward compatible — chat and unmatched tasks use static skills |
| Token budget cap (9000 tokens) | Prevent context overflow |
| Fallback to static | If chain selection fails, use current equipped skills |
| Subtasks are atomic | 1 subtask = 1 skill, no chain inheritance |
| No automatic chain switching | Complexity upgrade requires human decision |
| Title standardization | PROP/SPEC/DESIGN/VERIFY must use exact task title |
| chain_state is source of truth | Phase tracked on task, not derived from documents |
| Human approval gates | Chain steps with gates pause for human input |
| Metrics tracking | Track which dynamically selected skills were actually useful |

## Dependencies

- ES-0010 (skill metrics) — provides effectiveness data for Phase 3
- ES-0013 (spec-driven skills) — skills that need workflow-aware equipping
- Existing: skills table, agent_skills table, skill loading in AgentConfig

## Testing Strategy

This is a core change to how agents think — needs thorough testing:

### Unit Tests
- Chain matching: tag combos → correct chain selected
- Phase detection: chain_state → correct step returned
- Phase advancement: PROP/SPEC/DESIGN/VERIFY triggers → state advances
- Token budget: skills trimmed when over budget
- Fallback: no chain match → static skills used
- Keyword matching: title keywords → correct chain inferred

### Integration Tests
- Create task with `feature` + `high` tags → verify full chain loaded
- Agent stores `PROP: X` → verify chain advances to specify phase
- Agent discovers complex bug → verify chain switch flow (stop → re-tag → restart)
- Subtask creation → verify subtask gets single atomic skill
- Chat message without task keywords → verify static skills used
- Chat message with "research" keyword → verify task created + chain activated

### Regression Tests
- Static skill equipping still works (no chain context)
- Global skills always loaded regardless of chain
- Agent-specific skills always loaded
- Existing task pickup (no chain) works as before

## Estimated Effort

- Phase 1: 2 days (DB + seed script + make commands)
- Phase 2: 3-4 days (chain matching, skill loading rewrite, task-aware prompt generation)
- Phase 3: 2 days (chain_state tracking, auto-advancement, tool hooks)
- Phase 4: 1-2 days (human approval gates)
- Phase 5: 1 day (metadata recording + metrics integration)
- Phase 6: 1 day (skill_equip tool)
- Testing: 2 days (unit + integration + regression)
- **Total: ~12-14 days**
