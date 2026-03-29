# Phase 5: Scheduler & Autonomy

**Goal**: Agent runs a default heartbeat that checks for pending tasks and incoming messages, reports health, and fires configurable cron jobs for deeper task work.

**Delivers**: Agents are always alive — heartbeat catches new work quickly, cron handles sustained task sessions, health is always reported.

**Complexity**: Medium

## Dependencies

- Phase 1 (Foundation) — agent loop
- Phase 2 (Tool System) — platform tools (task_list, task_update)
- Phase 4 (Persistence) — DB connection pool, conversation history

## Two loops: heartbeat vs cron

| | Heartbeat | Cron (task check) |
|---|---|---|
| **Purpose** | Lightweight pulse — detect new work, report health | Full agent session — pick up tasks, do real work |
| **Interval** | Short: 60s default | Long: 30min default |
| **Cost** | Cheap — DB queries only, no LLM call | Expensive — triggers full agent loop with LLM |
| **What it does** | Check for pending tasks, unread messages, report health | Send prompt to agent: "check your queue, start working" |
| **Always on** | Yes — cannot be disabled | Configurable on/off |

The heartbeat is the "nervous system" — always checking. The cron is the "alarm clock" — periodically wakes the agent to do real work.

## What to build

### 5.1 Heartbeat (`scheduler/heartbeat.py`)

Lightweight loop that runs every 60s (configurable). No LLM calls — just DB checks and status reporting.

```python
class Heartbeat:
    def __init__(self, agent_name: str, agent_loop: AgentLoop):
        self.agent_name = agent_name
        self.agent_loop = agent_loop
        self._started_at = datetime.now(UTC)
        self._task: asyncio.Task | None = None

    async def start(self):
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        if self._task:
            self._task.cancel()

    async def _loop(self):
        interval = await self._get_interval()  # default 60s
        while True:
            try:
                await self._beat()
            except Exception as e:
                logger.error(f"Heartbeat error: {e}", exc_info=True)
            await asyncio.sleep(interval)

    async def _beat(self):
        """One heartbeat cycle."""
        # 1. Report health
        await self._report_health()

        # 2. Check for pending tasks
        pending = await self._check_pending_tasks()
        if pending:
            logger.info(f"Heartbeat: {len(pending)} pending task(s) detected")
            await self._trigger_task_pickup(pending)

        # 3. Check for unread messages in agent's spaces
        unread = await self._check_unread_messages()
        if unread:
            logger.info(f"Heartbeat: {len(unread)} unread message(s)")
            await self._trigger_message_response(unread)

    async def _report_health(self):
        """Update agent status in DB."""
        async with get_connection() as conn:
            await conn.execute(
                f"""INSERT INTO {SCHEMA}.agent_status
                    (agent_name, openclaw_healthy, details, checked_at)
                    VALUES (%s, TRUE, %s, NOW())""",
                (self.agent_name, json.dumps({
                    "runtime": "inotagent",
                    "uptime_seconds": (datetime.now(UTC) - self._started_at).total_seconds(),
                })),
            )
            await conn.execute(
                f"UPDATE {SCHEMA}.agents SET status = 'online', last_seen = NOW() WHERE name = %s",
                (self.agent_name,),
            )

    async def _check_pending_tasks(self) -> list[dict]:
        """Check for new todo tasks assigned to this agent."""
        async with get_connection() as conn:
            rows = await conn.execute(
                f"""SELECT key, title, priority, created_by
                    FROM {SCHEMA}.tasks
                    WHERE assigned_to = %s AND status = 'todo'
                    ORDER BY
                        CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                                      WHEN 'medium' THEN 2 ELSE 3 END,
                        created_at ASC""",
                (self.agent_name,),
            ).fetchall()
        return [dict(r) for r in rows]

    async def _trigger_task_pickup(self, tasks: list[dict]):
        """If agent is idle (not currently in a conversation), trigger task pickup via agent loop."""
        if self.agent_loop.is_busy():
            return  # Don't interrupt active work

        top = tasks[0]
        prompt = (
            f"You have a pending task: {top['key']} [{top['priority']}] \"{top['title']}\" "
            f"(assigned by {top['created_by']}). "
            f"Set it to in_progress and start working on it. "
            f"Use the opencode tool for all coding work."
        )
        conversation_id = f"heartbeat-task-{self.agent_name}-{top['key']}"
        asyncio.create_task(self.agent_loop.run(prompt, conversation_id, channel_type="cron"))

    async def _check_unread_messages(self) -> list[dict]:
        """Check for unread platform messages directed to this agent."""
        async with get_connection() as conn:
            rows = await conn.execute(
                f"""SELECT m.id, m.from_agent, m.body, s.name as space_name
                    FROM {SCHEMA}.messages m
                    JOIN {SCHEMA}.spaces s ON s.id = m.space_id
                    JOIN {SCHEMA}.space_members sm ON sm.space_id = s.id
                    WHERE sm.agent_name = %s
                      AND m.from_agent != %s
                      AND m.created_at > COALESCE(
                          (SELECT MAX(checked_at) FROM {SCHEMA}.agent_status WHERE agent_name = %s),
                          NOW() - INTERVAL '1 hour'
                      )
                    ORDER BY m.created_at ASC""",
                (self.agent_name, self.agent_name, self.agent_name),
            ).fetchall()
        return [dict(r) for r in rows]

    async def _trigger_message_response(self, messages: list[dict]):
        """Feed unread platform messages into agent loop."""
        if self.agent_loop.is_busy():
            return

        summary = "\n".join(f"- @{m['from_agent']} in #{m['space_name']}: {m['body']}" for m in messages)
        prompt = f"You have unread messages:\n{summary}\n\nRespond appropriately."
        conversation_id = f"heartbeat-messages-{self.agent_name}-{date.today()}"
        asyncio.create_task(self.agent_loop.run(prompt, conversation_id, channel_type="cron"))

    async def _get_interval(self) -> int:
        """Read heartbeat interval from config, default 60s."""
        async with get_connection() as conn:
            row = await conn.execute(
                f"SELECT value FROM {SCHEMA}.config WHERE key = 'heartbeat.interval_seconds'"
            ).fetchone()
        return int(row["value"]) if row else 60
```

### 5.2 AgentLoop.is_busy()

Add a simple busy check to the agent loop (from Phase 1):

```python
class AgentLoop:
    def __init__(self, ...):
        ...
        self._active_count = 0

    def is_busy(self) -> bool:
        """True if agent is currently processing a conversation."""
        return self._active_count > 0

    async def run(self, message, conversation_id, channel_type="cli"):
        async with self._semaphore:
            self._active_count += 1
            try:
                return await self._run_inner(message, conversation_id, channel_type)
            finally:
                self._active_count -= 1
```

### 5.3 Scheduler / Cron (`scheduler/cron.py`)

The heavier scheduled prompts — full agent loop sessions on a timer:

```python
class Scheduler:
    def __init__(self, agent_loop: AgentLoop, agent_name: str):
        self.agent_loop = agent_loop
        self.agent_name = agent_name
        self._tasks: list[asyncio.Task] = []

    async def start(self):
        """Load schedule config from DB and start recurring tasks."""
        config = await self._load_cron_config()

        if config.get("task_check.enabled", "true") == "true":
            interval = int(config.get(
                f"task_check.{self.agent_name}.interval_minutes",
                config.get("task_check.interval_minutes", "30"),
            ))
            prompt = self._get_task_check_prompt()
            self._tasks.append(
                asyncio.create_task(self._run_recurring("task_check", interval * 60, prompt))
            )

    async def stop(self):
        for task in self._tasks:
            task.cancel()

    async def _run_recurring(self, name: str, interval_seconds: int, prompt: str):
        """Run a prompt on a recurring interval."""
        while True:
            await asyncio.sleep(interval_seconds)
            try:
                conversation_id = f"cron-{name}-{self.agent_name}-{date.today()}"
                logger.info(f"Cron [{name}] firing for {self.agent_name}")
                await self.agent_loop.run(prompt, conversation_id, channel_type="cron")
                logger.info(f"Cron [{name}] completed for {self.agent_name}")
            except Exception as e:
                logger.error(f"Cron [{name}] failed: {e}", exc_info=True)
```

### 5.4 Role-based prompts

Different prompts for workers vs managers:

```python
AGENT_ROLES = {
    "ino": "manager",
    "robin": "worker",
}

TASK_CHECK_PROMPTS = {
    "worker": (
        "Check your task queue for pending work. "
        "List your assigned tasks with status todo or in_progress. "
        "If you have todo tasks, pick the highest priority one, set it to in_progress, and start working on it. "
        "If you have in_progress tasks, continue working on them. "
        "If no tasks, report that you are idle. "
        "IMPORTANT: For all coding work, use the opencode tool. "
        "NEVER write or edit code files directly — always delegate coding to opencode."
    ),
    "manager": (
        "Check task progress and follow up. "
        "List all tasks with status in_progress, blocked, or review. "
        "For blocked tasks: investigate and help unblock. "
        "For review tasks: review the work and approve if good. "
        "For stale in_progress tasks (no update in 2+ hours): follow up with the assigned agent. "
        "Report any issues to Boss via Discord."
    ),
}

def _get_task_check_prompt(self) -> str:
    role = AGENT_ROLES.get(self.agent_name, "worker")
    return TASK_CHECK_PROMPTS[role]
```

### 5.5 Config from DB

Read config from `platform.config` table:

```python
async def _load_cron_config(self) -> dict:
    """Load cron.* keys from platform.config."""
    async with get_connection() as conn:
        rows = await conn.execute(
            f"SELECT key, value FROM {SCHEMA}.config WHERE key LIKE 'cron.%%'"
        ).fetchall()

    config = {}
    for row in rows:
        short_key = row["key"].removeprefix("cron.")
        config[short_key] = row["value"]
    return config
```

Config keys (existing + new):

| Key | Default | Description |
|-----|---------|-------------|
| `heartbeat.interval_seconds` | `60` | Heartbeat cycle interval |
| `heartbeat.enabled` | `true` | Enable/disable heartbeat |
| `cron.task_check.enabled` | `true` | Enable/disable task check cron |
| `cron.task_check.interval_minutes` | `30` | Default task check interval |
| `cron.task_check.ino.interval_minutes` | `60` | Ino override (manager) |
| `cron.task_check.robin.interval_minutes` | `30` | Robin override (worker) |
| `memory.max_chars` | `8000` | Max chars (~2K tokens) returned per memory_search |
| `memory.short_term_days` | `30` | Auto-prune short-term memories older than this |
| `memory.trigger_keywords` | `remember,recall,last time,...` | Comma-separated keywords that auto-inject memory into prompt |
| `conversations.retention_days` | `30` | Auto-delete conversations older than this |

### 5.6 Config hot-reload

Periodically re-read config from DB to pick up changes without restart:

```python
async def _config_reload_loop(self, interval: int = 300):
    """Re-read config every 5 minutes. Adjust intervals if changed."""
    while True:
        await asyncio.sleep(interval)
        new_config = await self._load_cron_config()
        # Compare with current config, reschedule if intervals changed
```

### 5.7 Data pruning

Clean up old records to prevent table bloat. Runs once daily via heartbeat.

```python
async def _prune_old_data(self):
    """Daily cleanup of stale data."""
    async with get_connection() as conn:
        # Health records: keep 24 hours
        await conn.execute(
            f"DELETE FROM {SCHEMA}.agent_status WHERE checked_at < NOW() - INTERVAL '24 hours'"
        )
        # Short-term memories: keep 30 days. Long-term: never pruned.
        await conn.execute(
            f"DELETE FROM {SCHEMA}.memories WHERE tier = 'short' AND created_at < NOW() - INTERVAL '30 days'"
        )
        # Conversations: keep 30 days
        await conn.execute(
            f"DELETE FROM {SCHEMA}.conversations WHERE created_at < NOW() - INTERVAL '30 days'"
        )
```

| Table | Retention | Reason |
|-------|-----------|--------|
| `agent_status` | 24 hours | Health records, high volume, only recent matters |
| `memories (short)` | 30 days | Recent context, decisions, status updates |
| `memories (long)` | Never | Durable knowledge — scripts, patterns, preferences |
| `conversations` | 30 days | Chat history, mainly useful for recent context |

### 5.8 Entry point integration

```python
async def main():
    # ... setup agent loop, channels ...

    # Start heartbeat (always on)
    heartbeat = Heartbeat(agent_name, agent_loop)
    await heartbeat.start()

    # Start cron scheduler
    scheduler = Scheduler(agent_loop, agent_name)
    await scheduler.start()

    # Start channels (Discord, etc.)
    if channels.has_channels():
        await channels.start_all()
    else:
        await cli_mode(agent_loop)

    await scheduler.stop()
    await heartbeat.stop()
```

## How heartbeat and cron work together

```
Timeline:

0s     heartbeat: health OK, 0 pending tasks
60s    heartbeat: health OK, 1 new task detected → triggers agent loop (task pickup)
120s   heartbeat: health OK, agent busy (working on task)
180s   heartbeat: health OK, agent busy
...
1800s  cron: "check your task queue" → full agent session (deeper check, follow-ups)
1860s  heartbeat: health OK, agent busy (cron session)
...
```

Heartbeat catches new work quickly (within 60s). Cron does periodic deep reviews (every 30min). They don't conflict — heartbeat skips task pickup if the agent is already busy.

## Files to create/modify

| File | Action |
|------|--------|
| `src/inotagent/scheduler/__init__.py` | Create |
| `src/inotagent/scheduler/heartbeat.py` | Create — heartbeat loop |
| `src/inotagent/scheduler/cron.py` | Create — scheduled task prompts |
| `src/inotagent/loop.py` | Modify — add `is_busy()` method |
| `src/inotagent/main.py` | Modify — start heartbeat + scheduler |
| `tests/test_scheduler.py` | Create — heartbeat + cron tests |

## Existing code to port

- `core/runtime/healthcheck.py` — health reporting pattern, agent_status writes
- `core/runtime/setup_crons.py` — role-based prompts, interval config
- `core/runtime/config_sync.py` — config reload pattern

## How to verify

1. Start agent → check logs every 60s: "Heartbeat: health OK"
2. Create a todo task assigned to the agent → within 60s, heartbeat detects it and triggers pickup
3. Agent is busy working → heartbeat skips task pickup (logs "agent busy")
4. Wait for cron interval → "Cron [task_check] firing" in logs
5. Change `heartbeat.interval_seconds` in DB → agent picks up new interval on config reload
6. Set `cron.task_check.enabled = false` → cron stops, heartbeat continues
7. Agent status table shows regular health reports with uptime
8. Old health records pruned after 24 hours
