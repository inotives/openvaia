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

## Guardrails

**DO:**
- Create a task before starting any autonomous work (tagged `autonomous:true`)
- Complete one action per idle cycle, then wait for the next heartbeat
- Keep autonomous work focused and time-bounded (< 10 minutes)
- Report findings — don't just work silently

**DO NOT:**
- Start multiple autonomous tasks at once
- Ignore incoming human messages (they always take priority)
- Spend excessive tokens on low-value exploration
- Create tasks for other agents without human approval
- Repeat work you've already done recently (check last_completed_at)

## Autonomous Task Format

When creating a self-directed task:
```
Title: [Clear description of what you're doing]
Tags: autonomous:true, [relevant domain tags]
Priority: low
```

This ensures all autonomous work is visible and filterable in the admin UI.
