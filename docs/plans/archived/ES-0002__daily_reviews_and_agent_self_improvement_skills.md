# Daily Reviews & Agent Self-Improvement Skills — Execution Plan

## Backstory

Agents process many conversations and research tasks throughout the day, but most of that context lives only in conversation history — which has a retention window (30 days) and isn't searchable by meaning. When an agent is asked "what did you find out about X last week?", it relies on `memory_search`, but memories are only stored when the agent explicitly calls `memory_store` during a conversation. Most insights, decisions, and findings are never persisted to long-term memory.

This means agents gradually lose context. A research report from two weeks ago might be in the research DB, but the reasoning behind it, the dead ends explored, and the key takeaways are gone.

On top of that, agents develop implicit workflows through repeated work — patterns like "Boss prefers comparison tables in research reports" or "always check GeckoTerminal before Birdeye for Solana data" — but these patterns live only in conversation history and eventually expire. There's no mechanism for agents to formalize what they've learned into reusable knowledge.

## Purpose

Two interconnected features:

1. **Daily Review** — A 00:00 UTC cron job where each agent reviews its past 24 hours of work (tasks, research) and stores a structured summary in long-term memory. This creates a daily "journal entry" that the hybrid memory search (FTS + embedding) can surface in future conversations. Over time, agents build a rich long-term memory that compounds.

2. **Agent Self-Created Skills** — During the daily review, agents can notice repeatable patterns, recurring corrections, or workflow insights and formalize them as **draft skills**. Draft skills go through a human review process before being activated. This closes the loop: agents learn from experience → propose formalized knowledge → humans approve → knowledge becomes part of the agent's system prompt.

---

## Part 1: Daily Review

### How It Works

```
00:00 UTC — daily_review cron fires
        ↓
Agent queries own tasks from past 24h (task_list)
        ↓
Agent queries own research reports from past 24h (research_search)
        ↓
Agent sends to LLM: "Review today's work and summarize key insights"
        ↓
LLM returns structured summary
        ↓
Agent stores summary via memory_store(tier="long", tags=["daily_review", "YYYY-MM-DD"])
        ↓
Summary is embedded (pgvector) automatically — searchable by meaning forever
        ↓
If patterns detected → agent creates draft skill (see Part 2)
```

### What Gets Reviewed

- **Tasks**: Tasks completed, started, or updated in the past 24h (via `task_list`)
- **Research reports**: Reports created or updated in the past 24h (via `research_search`)
- **Implicit context**: The agent reflects on what it recalls from the day's work

Note: Direct conversation history access is out of scope for v1. Tasks and research cover ~80% of the value. A `conversation_summary` tool can be added later.

### What Gets Stored

A single long-term memory entry per day, tagged with `daily_review` and the date. The LLM decides what's worth remembering.

Example memory content:
```
## Daily Review — 2026-03-22

### Research
- Investigated Raydium DEX on Solana. Largest by TVL (~$800M). API: api.raydium.io/v2/main/info
- Explored Birdeye and GeckoTerminal APIs — Birdeye requires paid key, GeckoTerminal free

### Tasks
- Completed INO-003: DeFi yield aggregator research. Delivered report comparing 5 protocols.
- Started INO-004: Solana DEX volume pipeline. Blocked on API rate limits.

### Key Takeaways
- GeckoTerminal is most reliable free API for Solana DEX data
- Boss prefers research reports with comparison tables, not just prose
- Raydium API returns stale data occasionally — cross-reference with on-chain

### Patterns Noticed
- This is the third time Boss asked for comparison-style reports → consider creating a skill for research report formatting
```

### Cron Prompt (Draft)

```
Perform your daily review. Summarize your work from the past 24 hours.

Steps:
1. Check your tasks — list tasks you worked on today (any status change today)
2. Check your research — search for reports you created or updated today
3. Reflect on the day — what key decisions, findings, or instructions came up?

Store a summary in long-term memory:
- memory_store(content="## Daily Review — <today's date>\n\n<summary>", tags=["daily_review", "<today's date>"], tier="long")

Focus on:
- Key findings and data points worth remembering
- Decisions made and their reasoning
- Patterns or preferences expressed by Boss
- Unresolved questions or blockers
- Lessons learned (what worked, what didn't)

If you notice a repeatable pattern, recurring correction, or workflow that should be
formalized — create a draft skill using skill_create (see your self_improvement skill
for guidance). Draft skills will be reviewed by a human before activation.

Keep the review concise — aim for the most useful information for your future self.
```

---

## Part 2: Agent Self-Created Skills

### The Problem

Agents currently have a `self_improvement` skill that tells them to store lessons in memory. But memories are unstructured text — they help with recall but don't change how the agent behaves. A memory saying "Boss prefers comparison tables" only helps if the agent happens to search for it at the right time.

Skills, on the other hand, are injected into the system prompt every request — they're always-on behavioral rules. If "research_report_format" is a skill, the agent follows it on every research task without needing to remember to search for it.

### How It Works

```
Daily review detects pattern
        ↓
Agent calls: skill_create(
    name="research_report_format",
    description="Standard format for research reports",
    content="## Research Report Format\n\nAlways include:\n- Executive summary...",
    tags=["research", "formatting"],
    status="draft"
)
        ↓
Draft skill appears in Admin UI Skills page with "draft" badge
        ↓
Human reviews in UI:
  - Approve → status changes to "active", can be equipped
  - Edit → human refines content, then approves
  - Reject → status changes to "rejected" (kept for audit)
        ↓
Active skill auto-equipped to the creating agent (or manually assigned)
        ↓
Next heartbeat refresh → skill loaded into system prompt
```

### Skill Status Lifecycle

```
draft → active      (human approves)
draft → rejected    (human rejects)
active → inactive   (human disables)
```

Only `active` skills are loaded into the agent's system prompt. Draft and rejected skills are visible in the UI for review but never injected.

### When Do Agents Create Skills?

**Primary trigger: Daily review** — The daily review prompt includes an instruction to formalize patterns as draft skills. This is the natural moment — the agent is already reflecting on its work.

Examples of what agents might propose:
- "Boss always asks me to include token contract addresses in crypto research" → draft skill: `crypto_research_checklist`
- "When coding tasks involve migrations, I should always check existing migration files first" → draft skill: `migration_safety`
- "API rate limit workaround: batch requests with 1s delay for GeckoTerminal" → draft skill: `api_rate_limit_patterns`

**Future trigger: Weekly synthesis** — A weekly cron (e.g., Sunday 00:00 UTC) that reviews the past 7 daily reviews and asks "Are there patterns across this week that should become a skill?" This catches slow-emerging patterns not obvious in a single day.

### Database Changes

**`skills` table** — Add `status` column:

```sql
ALTER TABLE platform.skills ADD COLUMN status VARCHAR(16) NOT NULL DEFAULT 'active'
    CHECK (status IN ('draft', 'active', 'rejected', 'inactive'));
ALTER TABLE platform.skills ADD COLUMN created_by VARCHAR(64);
```

- `status`: controls whether the skill is loaded into system prompt (`active` only)
- `created_by`: tracks who created it — `NULL` or human name for manually created, agent name for self-created

**Skills loader** (`db/skills.py`) — Filter to `status = 'active'` when loading skills for system prompt injection.

**Admin UI** — Skills page shows status badge (draft/active/rejected/inactive) with approve/reject actions for drafts.

### New Tool: skill_create

A new tool (or extension of existing skill tools) that agents can call:

```python
SKILL_CREATE_TOOL = {
    "name": "skill_create",
    "description": "Propose a new skill as a draft. It will be reviewed by a human before activation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Skill name (snake_case)"},
            "description": {"type": "string", "description": "One-line description"},
            "content": {"type": "string", "description": "Skill content (markdown)"},
            "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for categorization"},
        },
        "required": ["name", "description", "content", "tags"],
    },
}
```

The handler inserts into `skills` with `status='draft'` and `created_by=agent_name`. This becomes tool #16.

---

## Development Steps

### Step 1: Migration — skills status + daily_review cron

**File**: `infra/postgres/migrations/YYYYMMDD_add_skill_status_and_daily_review.sql`

- Add `status` column to `skills` table (default `active` for existing skills)
- Add `created_by` column to `skills` table
- Seed `daily_review` cron job (1440 min interval, global with per-agent override)
- Seed `daily_review` skill with instructions on review format

Estimated: ~30 lines

### Step 2: Update skills loader

**File**: `inotagent/src/inotagent/db/skills.py`

- Filter skills query to `WHERE status = 'active'` (currently loads all)

Estimated: ~5 lines

### Step 3: Daily review cron prompt

**File**: `inotagent/src/inotagent/scheduler/cron.py`

- Add `DAILY_REVIEW_PROMPT` constant

Estimated: ~25 lines

### Step 4: skill_create tool

**File**: `inotagent/src/inotagent/tools/platform.py` (or new file)

- `skill_create` handler: insert into `skills` with `status='draft'`, `created_by=agent_name`
- Add tool definition

**File**: `inotagent/src/inotagent/tools/setup.py`

- Register `skill_create` as tool #16

Estimated: ~40 lines

### Step 5: Admin UI — skill status + review actions

**File**: `ui/src/app/skills/page.tsx`

- Show status badge (draft=orange, active=green, rejected=red, inactive=grey)
- Add "Approve" / "Reject" buttons for draft skills
- Filter dropdown: all / draft / active / rejected

**File**: `ui/src/app/api/skills/[id]/route.ts`

- `PATCH` handler to update skill status

Estimated: ~50 lines

### Step 6: Tests

**File**: `inotagent/tests/test_scheduler.py`

- Test `DAILY_REVIEW_PROMPT` exists and contains key instructions
- Test daily_review cron seeding

**File**: `inotagent/tests/test_tools.py`

- Test `skill_create` tool inserts with `status='draft'`
- Test `skill_create` sets `created_by` to agent name

**File**: `inotagent/tests/test_persistence.py`

- Test skills loader filters by `status='active'`

**File**: `tests/test_ui.py`

- Test skill status PATCH endpoint

Estimated: ~40 lines

---

## Summary

| Component | File(s) | Lines |
|---|---|---|
| Migration (status + cron + skill seed) | `infra/postgres/migrations/` | ~30 |
| Skills loader filter | `db/skills.py` | ~5 |
| Daily review cron prompt | `scheduler/cron.py` | ~25 |
| skill_create tool | `tools/platform.py` + `setup.py` | ~40 |
| Admin UI (status + review) | `skills/page.tsx` + `skills/[id]/route.ts` | ~50 |
| Tests | `test_scheduler.py` + `test_tools.py` + `test_persistence.py` + `test_ui.py` | ~40 |
| **Total** | | **~190 lines** |

No new dependencies. No new containers. One migration. One new tool (#16).

---

## Future Enhancements

- **Weekly synthesis cron** — reviews 7 daily reviews, proposes higher-level skills from emerging patterns
- **Conversation review tool** — `conversation_summary(hours=24)` for richer daily reviews
- **Cross-agent skill sharing** — agent A's approved skill can be suggested to agent B if tags match
- **Skill versioning** — track edits to skills over time, diff view in UI
- **Auto-approve trusted agents** — after N approved drafts, skip human review for low-risk skills
- **Skill effectiveness tracking** — measure if a skill actually changes agent behavior (before/after comparison)


## Status: DONE
