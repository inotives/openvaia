---
name: idle_behavior
description: Guides autonomous behavior when idle — check mission board, update stale research, discover resources
tags: [workflow, autonomous, proactive]
source: openvaia/ES-0009
---
# Idle Behavior

When you have no in-progress tasks and no pending messages, follow this protocol to stay productive.

## Idle Detection

You are idle when ALL of these are true:
- No tasks with status `in_progress` assigned to you
- No unread messages in your channels
- No pending human conversations

## Idle Action Priority (pick ONE per cycle)

Work through this list in order. Do the first action that applies, then stop.

### 1. Check Mission Board
Search for unclaimed `backlog` tasks that match your skills and mission tags.
- If found: self-assign, set to `todo`, and begin work
- Only pick tasks you're qualified for based on your role

### 2. Follow Up on Stale Research
Check your recent research reports (last 7 days).
- Is any data outdated? (price data, market conditions, API status)
- If yes: create a follow-up task to refresh the data
- Don't re-research everything — only what's meaningfully stale

### 3. Review Curated Resources
Search curated resources for new content added in the last 24 hours.
- If new resources found: scan for relevance to your domain
- If relevant: create a brief analysis or summary as a research report

### 4. Proactive Monitoring
Based on your role, check for conditions that warrant attention:
- **Financial researchers**: significant market movements, breaking news
- **Operations engineers**: system health anomalies, failed jobs, resource usage

### 5. Status Update
If none of the above apply, post a brief status update to your space:
- What you completed recently
- What you're waiting on
- Any observations or suggestions

## Anti-Repetition Rules (CRITICAL)

Before starting ANY autonomous action:

1. **Check your recent tasks first** — run `task_list` and review the last 10 tasks you completed
2. **Do NOT repeat the same type of work** — if you already did "market health check" or "refresh crypto prices" in the last 3 hours, pick a DIFFERENT action
3. **Vary your activities** — cycle through different idle actions (research → resources → monitoring → status update) instead of repeating the same one
4. **If all idle actions were done recently**, do nothing — skip this cycle entirely and wait for the next heartbeat

**Examples of repetition to AVOID:**
- Creating "Proactive market health check" 5 times in a row
- Refreshing the same API data every idle cycle
- Running the same monitoring check repeatedly

**Good variety pattern:**
- Cycle 1: Check mission board
- Cycle 2: Review stale research
- Cycle 3: Explore new resources
- Cycle 4: Monitor for breaking news
- Cycle 5: Write status update
- Cycle 6: Skip (nothing new to do)

## Guardrails

**DO:**
- Create a task before starting any autonomous work (tagged `autonomous:true`)
- **Always assign the task to yourself** (assigned_to = your name)
- Complete one action per idle cycle, then wait for the next heartbeat
- Keep autonomous work focused and time-bounded (< 10 minutes)
- Report findings — don't just work silently
- **Check recent tasks before acting to avoid repetition**

**DO NOT:**
- Start multiple autonomous tasks at once
- Ignore incoming human messages (they always take priority)
- Spend excessive tokens on low-value exploration
- Create tasks for other agents without human approval
- **Repeat the same type of work within 3 hours**
- Create tasks without assigning them to yourself
- Do the same monitoring check more than once per hour

## Autonomous Task Format

When creating a self-directed task:
```
Title: [Clear, UNIQUE description — not the same as recent tasks]
Tags: autonomous:true, [relevant domain tags]
Priority: low
Assigned to: [your name]
```

This ensures all autonomous work is visible and filterable in the admin UI.
