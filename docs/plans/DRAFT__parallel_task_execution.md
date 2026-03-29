# Parallel Task Execution — DRAFT

> **Status**: In discussion. Not finalized.

## Problem

Agents currently process tasks sequentially — one LLM chain at a time. When multiple tasks are due simultaneously (e.g., recurring tasks at the top of the hour), they queue up and later tasks are delayed by however long earlier ones take.

The `parallel` flag already exists in `agent_configs` but is not fully implemented.

## Questions to Resolve

### 1. Concurrency Model

How should parallel execution work?

- **Option A: Multiple asyncio tasks** — spawn multiple `agent_loop.run()` calls concurrently within the same process. Simplest to implement but shares memory, DB pool, and tool state.
- **Option B: Worker pool** — a fixed number of worker slots (e.g., `parallel=3` means 3 concurrent chains). Tasks are dispatched to available workers.
- **Option C: Per-task containers** — spin up ephemeral containers for parallel work. Heaviest but cleanest isolation.

Leaning toward **Option A or B** — Option C is overkill for the problem.

### 2. Resource Contention

What happens when two concurrent tasks use the same tools?

- **Shell**: Two tasks running shell commands in the same `/workspace` could conflict (e.g., both trying to `git checkout` different branches)
- **Files**: Concurrent writes to the same file
- **Discord**: Two tasks trying to post to the same channel simultaneously (message ordering)
- **Memory**: Both tasks calling `memory_store` at the same time (should be fine — DB handles concurrency)
- **Browser**: Playwright instance — can it handle multiple pages concurrently?

Need to categorize tools as:
- **Safe for parallel**: memory_store, memory_search, research_store, research_search, task_list, task_update, send_message
- **Needs locking**: shell, read_file, write_file, browser
- **Needs isolation**: git operations (different working directories per task)

### 3. Conversation Isolation

Each parallel task needs its own conversation context — otherwise messages from Task A would appear in Task B's LLM history. Currently `conversation_id` handles this (e.g., `cron-task_check-robin-2026-03-25`). Parallel tasks would naturally have different conversation IDs, so this may already work.

### 4. Token Budget

Two concurrent LLM calls consume 2x the tokens and 2x the rate limit budget. With NVIDIA NIM free tier's ~40 req/min limit, parallel execution could hit rate limits faster. Fallback chains would help, but concurrent chains competing for the same fallback model could cascade failures.

### 5. How Many Parallel Slots?

- `parallel=1` (default) — sequential, current behavior
- `parallel=2-3` — reasonable for a single agent
- `parallel=5+` — likely hitting rate limits and resource contention

The `parallel` config value could control the max concurrent workers.

### 6. Priority When Slots Are Full

If all parallel slots are busy and a new high-priority task arrives, should it:
- Wait in queue (FIFO)?
- Preempt a lower-priority running task?
- Just queue behind — the heartbeat will pick it up next cycle?

Simplest: just queue. Preemption adds significant complexity.

## Rough Implementation Sketch

```python
class AgentLoop:
    def __init__(self, ..., max_parallel=1):
        self._semaphore = asyncio.Semaphore(max_parallel)
        self._active_tasks = set()

    async def run_parallel(self, task_key, prompt, conversation_id):
        async with self._semaphore:
            self._active_tasks.add(task_key)
            try:
                return await self.run(prompt, conversation_id=conversation_id)
            finally:
                self._active_tasks.discard(task_key)

    def is_busy(self):
        return len(self._active_tasks) >= self._max_parallel
```

Heartbeat would call `run_parallel` instead of `run` when dispatching tasks, and `is_busy()` would check against the semaphore count instead of a single boolean.

## Primary Use Case: Recurring Task Collisions

With ES-0006 (recurring tasks) now implemented and cron disabled, the most common collision scenario is:

```
00:00 UTC → heartbeat resets 3 tasks simultaneously:
  - Daily market report (schedule:daily@00:00)
  - Hourly data check (schedule:hourly)
  - Monthly review (schedule:monthly@00:00)
→ Currently: sequential — task 1 blocks task 2 and 3
→ Desired: all 3 run concurrently
```

### Practical Middle Ground: Recurring-Only Parallelism

Instead of full parallel execution for all tasks, start with parallelism **only for recurring tasks**:

1. When heartbeat resets multiple recurring tasks, spawn each as a separate `asyncio.create_task(agent.run(...))`
2. Each gets its own `conversation_id` (already unique per task key)
3. Bypass the `is_busy()` check for recurring tasks specifically
4. Regular (non-recurring) tasks still queue sequentially

This is safer because:
- Recurring tasks tend to be **read-heavy** (research, reports, summaries) not write-heavy (code changes)
- They typically don't touch the same files or repos
- Their prompts are pre-defined and scoped, reducing unpredictable tool conflicts

### Implementation Sketch

```python
# In heartbeat._reset_recurring_tasks():
for task in reset_tasks:
    asyncio.create_task(
        self.agent_loop.run(
            task["description"] or task["title"],
            conversation_id=f"recurring-{task['key']}-{date.today()}",
            channel_type="recurring",
        )
    )
```

### Remaining Risks Even With Recurring-Only

- **LLM rate limits**: 3 concurrent LLM calls = 3x rate limit consumption. Mitigated by fallback chain.
- **Discord flooding**: 3 tasks posting results to Discord simultaneously. Mitigated by message queue or slight delay.
- **Memory store conflicts**: Multiple `memory_store` calls at once — DB handles this fine (each is its own INSERT).

## Dependencies

- ~~ES-0006 (Recurring Tasks) should land first~~ — **DONE**
- Tool locking/isolation design should be finalized before implementation

## Estimated Effort

Medium. For recurring-only parallelism: ~30 lines in heartbeat + conversation isolation testing. Probably half a day.

Full parallel execution (all tasks): medium-large, 1-2 days.

## Decision Needed

1. Which concurrency model? (A, B, or C)
2. Which tools need locking vs are safe?
3. **Start with recurring-only parallelism?** (recommended — lower risk, solves the immediate problem)
4. What's the default `parallel` value for existing agents?
5. Should this be a v1.x enhancement or v2?
