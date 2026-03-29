# Recurring Tasks — Replace Cron with Task-Based Scheduling — Execution Plan

## Backstory

The current cron system loads jobs from DB at agent boot and runs them on fixed UTC-aligned intervals. This works but has a significant friction point: **any new or deleted cron job requires an agent restart to take effect**. The agent has no way to pick up new crons at runtime because the scheduler loads once at startup.

We added a warning icon in the UI and restart buttons to mitigate this, but it's a workaround, not a fix. As the platform grows, operators will want to create ad-hoc recurring workflows (daily reports, hourly data checks, weekly digests) without restarting agents every time.

Meanwhile, the **task system already handles everything we need**: assignment, status tracking, priority, tags, and the heartbeat already checks for pending tasks every 60 seconds. The missing piece is just making tasks **repeat on a schedule**.

## Purpose

Replace cron-based scheduling with **recurring tasks** — tasks tagged with a schedule (e.g., `hourly`, `daily`, `weekly`) that automatically reset to `todo` when their interval is due. The existing heartbeat + task detection pipeline handles the rest — no new scheduler, no restart required.

New recurring tasks are picked up on the next heartbeat cycle (60s) instead of requiring a full agent restart.

## How It Works Today (Cron)

```
Boot → load cron_jobs from DB → start scheduler threads → fixed intervals
                                    ↓
                          New cron added to DB
                                    ↓
                          ⚠️ Agent doesn't know — restart required
```

## How It Would Work (Recurring Tasks)

```
Heartbeat (every 60s) → check tasks with recurrence tag
        ↓
Find tasks where:
  - status = 'done' or 'completed'
  - has recurrence tag (e.g., schedule:daily, schedule:hourly)
  - last_completed_at + interval < NOW()
        ↓
Reset task status to 'todo'
        ↓
Normal task pickup pipeline handles it (already exists)
        ↓
Agent picks up task → executes → marks done
        ↓
Next heartbeat cycle → checks again → resets when due
```

### Example: Daily Market Report

**Before (cron)**:
```
cron_jobs: name=daily_market_report, interval=1440, prompt="Generate daily market report..."
→ Requires agent restart to add/remove
```

**After (recurring task)**:
```
tasks: title="Daily Market Report", tags=["schedule:daily", "report", "market"]
       prompt/description="Research today's market movements and generate a report..."
       assigned_to=ino, status=todo
→ Agent picks up via normal task flow
→ After completion, heartbeat resets to todo after 24h
→ No restart needed to add new recurring tasks
```

### Schedule Tags Convention

Use tags to define recurrence:

| Tag | Interval | Use Case |
|---|---|---|
| `schedule:5m` | 5 minutes | Health checks, quick monitors |
| `schedule:15m` | 15 minutes | Data pipeline checks |
| `schedule:30m` | 30 minutes | Task queue review |
| `schedule:hourly` | 1 hour | Hourly reports, market snapshots |
| `schedule:4h` | 4 hours | Periodic research updates |
| `schedule:12h` | 12 hours | Twice-daily summaries |
| `schedule:daily` | 24 hours | Daily reports, reviews |
| `schedule:weekly` | 7 days | Weekly digests, retrospectives |

Tags are flexible — parsed at runtime, no schema change needed.

---

## Technical Design

### Database Changes

**`tasks` table** — Add columns:

```sql
ALTER TABLE platform.tasks ADD COLUMN last_completed_at TIMESTAMPTZ;
ALTER TABLE platform.tasks ADD COLUMN recurrence_minutes INTEGER;
```

- `last_completed_at`: timestamp of last completion (set when task moves to `done`)
- `recurrence_minutes`: parsed from `schedule:*` tag, cached for fast queries. NULL = one-time task.

Alternatively, skip `recurrence_minutes` column and parse from tags at query time — simpler schema but slightly slower queries. Recommend the column for clarity.

### Heartbeat Changes

**File**: `inotagent/src/inotagent/scheduler/heartbeat.py`

Add a new step in `_beat()` after task checking:

```python
async def _reset_recurring_tasks(self):
    """Reset completed recurring tasks that are due."""
    schema = get_schema()
    async with get_connection() as conn:
        # Find recurring tasks that are done and past their interval
        cur = await conn.execute(f"""
            UPDATE {schema}.tasks
            SET status = 'todo',
                updated_at = NOW()
            WHERE assigned_to = %s
              AND status = 'done'
              AND recurrence_minutes IS NOT NULL
              AND last_completed_at + (recurrence_minutes || ' minutes')::interval < NOW()
            RETURNING key, title
        """, (self.agent_name,))
        rows = await cur.fetchall()
        if rows:
            logger.info(f"Reset {len(rows)} recurring task(s): {[r['key'] for r in rows]}")
```

This runs every heartbeat (60s). When a recurring task's interval is due, it resets to `todo` — the existing task pickup logic handles the rest.

### Task Completion Hook

When a task moves to `done`, set `last_completed_at`:

**File**: `inotagent/src/inotagent/tools/platform.py` (task_update handler)

```python
# When status changes to 'done', set last_completed_at
if new_status == 'done':
    await conn.execute(f"""
        UPDATE {schema}.tasks SET last_completed_at = NOW() WHERE key = %s
    """, (key,))
```

### Tag Parsing

Parse `schedule:*` tags into `recurrence_minutes` on task creation/update:

```python
SCHEDULE_MAP = {
    "5m": 5, "15m": 15, "30m": 30,
    "hourly": 60, "4h": 240, "12h": 720,
    "daily": 1440, "weekly": 10080,
}

def parse_recurrence(tags: list[str]) -> int | None:
    for tag in tags:
        if tag.startswith("schedule:"):
            key = tag.split(":", 1)[1]
            return SCHEDULE_MAP.get(key)
    return None
```

### Migration: Convert Existing Crons to Recurring Tasks

A one-time migration that:
1. Reads existing `cron_jobs` entries
2. Creates equivalent tasks with `schedule:*` tags
3. Keeps `cron_jobs` table for backward compatibility (can be deprecated later)

### Admin UI Changes

**Tasks page** — recurring tasks show a recurrence badge (e.g., "🔄 daily") and `last_completed_at` in the detail drawer.

**Cron Jobs page** — add a deprecation notice: "Cron jobs are being replaced by recurring tasks. Use schedule tags on tasks instead."

### What Happens to `task_check` Cron?

The `task_check` cron becomes unnecessary — the heartbeat already checks for pending tasks every 60s. The recurring task reset logic runs in the same heartbeat cycle. We can increase heartbeat task checking to cover what `task_check` did, then disable the cron.

---

## Migration Path

This is a gradual transition, not a big bang:

1. **Phase 1**: Add recurring task support (DB columns, heartbeat logic, tag parsing). Both systems coexist.
2. **Phase 2**: Convert existing cron prompts to recurring tasks via Admin UI. Test side by side.
3. **Phase 3**: Deprecate cron UI (show notice). Stop creating new crons.
4. **Phase 4** (optional): Remove cron scheduler code entirely.

---

## Development Steps

### Step 1: Migration — task columns

**File**: `infra/postgres/migrations/YYYYMMDD_add_recurring_tasks.sql`

- Add `last_completed_at` and `recurrence_minutes` columns to `tasks`
- Index on `(assigned_to, status, recurrence_minutes)` for fast heartbeat queries

Estimated: ~15 lines

### Step 2: Tag parsing utility

**File**: `inotagent/src/inotagent/tools/platform.py`

- `parse_recurrence(tags)` function
- Set `recurrence_minutes` on task creation and update when tags contain `schedule:*`

Estimated: ~20 lines

### Step 3: Task completion hook

**File**: `inotagent/src/inotagent/tools/platform.py`

- Set `last_completed_at = NOW()` when task status changes to `done`

Estimated: ~5 lines

### Step 4: Heartbeat recurring task reset

**File**: `inotagent/src/inotagent/scheduler/heartbeat.py`

- Add `_reset_recurring_tasks()` method
- Call it in `_beat()` after existing task checks

Estimated: ~25 lines

### Step 5: Admin UI — recurring task badge

**File**: `ui/src/app/tasks/page.tsx` and `ui/src/app/agents/[name]/page.tsx`

- Show recurrence badge on tasks with `schedule:*` tags
- Show `last_completed_at` in task detail drawer

Estimated: ~20 lines

### Step 6: Tests

**File**: `inotagent/tests/test_scheduler.py`

- Test `_reset_recurring_tasks` resets done tasks past interval
- Test it skips tasks not yet due
- Test it skips one-time tasks (no recurrence_minutes)

**File**: `inotagent/tests/test_tools.py`

- Test `parse_recurrence` parses all schedule tags
- Test `last_completed_at` is set on task completion

Estimated: ~40 lines

---

## Summary

| Component | File(s) | Lines |
|---|---|---|
| Migration | `infra/postgres/migrations/` | ~15 |
| Tag parsing | `tools/platform.py` | ~20 |
| Completion hook | `tools/platform.py` | ~5 |
| Heartbeat reset | `scheduler/heartbeat.py` | ~25 |
| Admin UI badges | `tasks/page.tsx` + agent detail | ~20 |
| Tests | `test_scheduler.py` + `test_tools.py` | ~40 |
| **Total** | | **~125 lines** |

One migration. No new tools. No new dependencies. No restart required for new recurring tasks.

---

## Known Limitation: Sequential Execution

Recurring tasks execute **sequentially** — one at a time. If multiple tasks are due at the same time (e.g., daily report + hourly report both due at 00:00), they queue up:

```
00:00 → heartbeat resets both to "todo"
00:00 → agent picks up daily report (higher priority)
00:05 → daily report done
00:05 → agent picks up hourly report
00:08 → hourly report done (8 minutes late)
```

They won't crash or conflict — the second task simply waits. But it will be delayed by however long the first task takes.

**Mitigations for ES-0006:**

1. **Priority-based ordering** — higher priority tasks execute first. Operators should set critical recurring tasks (e.g., daily report) to `high` priority.
2. **Staggered schedules** — offset recurring tasks so they don't collide at the same time. For example, daily report at `schedule:daily` (resets at 00:00 UTC), hourly report with first run a few minutes later. Operationally, just create the hourly task a few minutes after the daily.
3. **Keep fast tasks fast** — recurring tasks should have focused prompts that complete quickly. Avoid open-ended research as a recurring task.

**Parallel task execution** (running multiple LLM chains concurrently) is tracked separately as a future enhancement — see `DRAFT__parallel_task_execution.md`.

---

## Benefits Over Cron

| | Cron | Recurring Tasks |
|---|---|---|
| Add new schedule | Requires agent restart | Next heartbeat (60s) |
| Remove schedule | Requires agent restart | Just delete the task |
| Status tracking | None (fire and forget) | Full task status flow |
| History | No record of past runs | Task history + `last_completed_at` |
| Visibility | Separate Cron Jobs page | Unified on Tasks/Kanban board |
| Assignment | Per-agent or global | Per-agent with reassignment |
| Priority | None | Full priority system |
| Dependencies | None | Parent/subtask hierarchy |

---

## Future Enhancements

- **Cron expression support** — `schedule:cron:0 9 * * MON` for complex schedules (every Monday 9am)
- **Run history** — track each execution as a subtask or log entry
- **Pause/resume** — temporarily stop recurrence without deleting the task
- **Execution window** — "only run between 09:00-17:00 UTC" for business-hours tasks
- **Missed run handling** — if agent was down, catch up on missed runs or skip to next
- **Parallel task execution** — run multiple recurring tasks concurrently (see `DRAFT__parallel_task_execution.md`)


## Status: DONE
