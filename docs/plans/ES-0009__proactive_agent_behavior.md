# ES-0009 — Proactive Agent Behavior

## Status: COMPLETE (Phase 1–3.5), Phase 4–5 deferred

## Problem / Pain Points

Agents are purely reactive — they sit idle until a human sends a message or a task is assigned. This wastes their potential:

- Agents idle 90%+ of the time between human interactions
- No autonomous exploration of their domain
- No self-initiated research or reporting
- No proactive monitoring of resources or market conditions
- Agents don't learn or improve without explicit human prompting

## Suggested Solution

Make agents proactive in a **controlled, observable** way. Agents should autonomously work on their domain during idle time, while respecting boundaries and reporting what they do.

### Phase 1: Recurring Exploration Tasks (no code changes)

Use the existing `schedule:` tag system to create recurring tasks per agent:

**ino (Global Financial Researcher):**

| Key | Title | Schedule | Description |
|-----|-------|----------|-------------|
| `INO-001` | Morning Market Brief | `schedule:daily@09:00` | Compile overnight market movements: BTC, ETH, gold, S&P 500. Key price levels, notable news, sentiment indicators. Post as research report. |
| `INO-002` | End of Day Market Summary | `schedule:daily@17:00` | Summarize the day's market activity: price changes, volume, notable events. Compare with morning brief. Post as research report. |
| `INO-003` | Price Alert Monitor | `schedule:hourly` | Check top 5 crypto assets (BTC, ETH, SOL, PAXG, XAU) for >5% price movements in the last hour. Post alert with analysis to Discord if detected. |
| `INO-004` | Resource Discovery | `schedule:daily@12:00` | Check curated resources for new research material. Search for recent reports, data sources, or tools relevant to crypto and macro research. |

**robin (Trading Operations Engineer):**

| Key | Title | Schedule | Description |
|-----|-------|----------|-------------|
| `ROB-001` | System Health Check | `schedule:daily@09:30` | Verify DB connections, check container status, review recent error logs, check disk usage. Report anomalies. |
| `ROB-002` | Daily Operations Log | `schedule:daily@18:00` | Review what ran today: heartbeat cycles, tasks processed, messages handled, any errors or timeouts. Write brief ops log. |
| `ROB-003` | Weekly Engineering Retro | `schedule:weekly@MON:10:00` | Run weekly retrospective: analyze git commits, work sessions, shipping streaks, test coverage trends. Use `engineering_retro` skill. |
| `ROB-004` | Review Mission Board | `schedule:daily@08:00` | Check mission board for unclaimed backlog tasks. If any match skills (coding, infrastructure, operations), self-assign and start working. |

All tasks created with `status: done` — heartbeat resets them at their scheduled times.

### Phase 2: Idle Behavior Skill (global skill)

Create `0__idle_behavior.md` — a global skill that activates when the agent has been idle for 5+ minutes:

```
When idle (no in-progress tasks, no pending messages):
1. Check mission board for unclaimed backlog tasks matching your tags
2. Review your recent research — is any data stale? Update it.
3. Check curated resources for new content to analyze
4. If nothing to do, create a brief status update in your space
5. Maximum 1 autonomous task per idle cycle (don't spiral)
```

**Guardrails:**
- Maximum 1 autonomous action per idle cycle
- All autonomous work creates a task first (observable in UI)
- Autonomous tasks tagged `autonomous:true` for filtering
- Human can disable via `agent_configs` setting: `proactive_enabled: false`
- Budget cap: max N autonomous LLM calls per day (configurable)

### Phase 3: Heartbeat Enhancement (code change)

Modify the heartbeat scheduler to add an idle detection phase:

```python
# In heartbeat.py
async def heartbeat_tick():
    await check_health()
    await reset_recurring_tasks()
    await check_mission_board()
    await check_messages()

    # NEW: Proactive behavior
    if agent_idle_for(minutes=5) and config.get("proactive_enabled", True):
        await run_idle_behavior()
```

`run_idle_behavior()` triggers the agent's reasoning loop with a prompt assembled from the `idle_behavior` skill, giving the agent context about:
- Current time and day
- Recent activity summary
- Available resources and tools
- Any pending items from previous autonomous work

### Phase 4: Inter-Agent Collaboration

Agents proactively create tasks for each other:
- ino finds interesting data → creates research task assigned to robin for technical analysis
- robin notices system anomaly → creates investigation task for ino to check market impact
- Uses existing `platform.tasks` + `platform.messages` for coordination
- Agent-to-agent messages in shared spaces for context

### Phase 5: Proactive Reporting & Notifications

- Agents push summaries to Discord/Slack without being asked
- Configurable notification channels per agent
- Smart batching — don't spam, collect and send at scheduled times
- Escalation: critical findings sent immediately, routine findings batched

### Phase 3.5: Human Message Priority (Interrupt Pattern)

When an agent is busy with autonomous work and a human message arrives, the agent must prioritize the human.

**Problem:** Agent reasoning loop runs synchronously — one request at a time. If an autonomous task takes 5-10 minutes, human messages queue until it finishes.

**Solution: Inter-iteration message check in `loop.py`**

Between each tool call iteration of the reasoning loop, check for pending human messages:

```python
# In loop.py — inside the reasoning loop
async def run_loop(agent, messages, ...):
    for iteration in range(max_iterations):
        response = await llm_call(messages)

        if response.has_tool_calls:
            results = await execute_tools(response.tool_calls)
            messages.append(results)

            # NEW: Check for pending human messages between iterations
            if agent.current_task_is_autonomous:
                pending = await check_pending_human_messages(agent)
                if pending:
                    # Pause autonomous work
                    await pause_current_task(agent, status="blocked",
                        result="Paused: human message received")
                    return PauseReason.HUMAN_PRIORITY

        else:
            # Final response, no more tool calls
            break
```

**Behavior:**
1. Agent starts autonomous task (tagged `autonomous:true`)
2. Human sends Discord/Slack/Telegram/web message
3. At the next iteration boundary (after current tool call completes), agent checks for pending messages
4. If found → saves current autonomous task as `blocked` with context
5. Handles human request with full attention
6. After human conversation ends → heartbeat picks up blocked autonomous task and resumes

**Key rules:**
- Only autonomous tasks are interruptible — human-initiated tasks are NOT interrupted
- Check happens between iterations, never mid-tool-call (safe pause point)
- Paused task saves progress context so it can resume intelligently
- Agent sends acknowledgment: "I was working on [X], pausing to help you."

**What counts as a pending human message:**
- New message in any channel (Discord, Slack, Telegram, web) where `role = 'user'`
- Message `created_at` is after the autonomous task started
- Message has not been processed yet (`processed_at IS NULL`)

**Implementation in `check_pending_human_messages()`:**
```python
async def check_pending_human_messages(agent) -> bool:
    rows = await db.fetch("""
        SELECT 1 FROM conversations
        WHERE agent_name = $1
          AND role = 'user'
          AND processed_at IS NULL
          AND created_at > $2
        LIMIT 1
    """, agent.name, agent.current_task_started_at)
    return len(rows) > 0
```

## Implementation Steps

- [x] Phase 1: Create recurring tasks for ino and robin (no code changes)
- [x] Phase 1: Verify recurring tasks execute on schedule
- [x] Phase 2: Create `0__idle_behavior.md` global skill
- [x] Phase 2: Test idle behavior activates correctly
- [x] Phase 3: Add idle detection to heartbeat scheduler
- [x] Phase 3: Add `proactive_enabled` config toggle
- [x] Phase 3: Add daily autonomous call budget
- [x] Phase 3.5: Detect autonomous conversations via `heartbeat-idle-` prefix
- [x] Phase 3.5: Add `_check_pending_human_messages()` to loop.py
- [x] Phase 3.5: Add inter-iteration message check + semaphore waiter check
- [x] Phase 3.5: Save pause note and return early on interrupt
- [ ] Phase 4: Inter-agent task creation (deferred)
- [ ] Phase 5: Proactive Discord notifications (deferred)
- [ ] Phase 5: Notification batching/scheduling (deferred)

## Guardrails & Safety

| Guardrail | Purpose |
|-----------|---------|
| `proactive_enabled` config toggle | Kill switch per agent |
| `autonomous:true` task tag | Filter/audit autonomous work |
| Max 1 action per idle cycle | Prevent runaway loops |
| Daily LLM call budget | Cost control |
| Task-first approach | All autonomous work is observable |
| Human message priority | Human messages interrupt autonomous work between iterations |
| Safe pause points | Only pause between iterations, never mid-tool-call |
| Resume capability | Paused tasks save context for intelligent resumption |

## Success Criteria

- Agents produce useful output without human prompting
- Autonomous work is visible and auditable (tasks, reports)
- No runaway costs or infinite loops
- Humans can easily enable/disable/configure proactive behavior
- Agents move between office rooms based on autonomous activity
