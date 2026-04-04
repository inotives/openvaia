---
name: task_management
description: How to create, delegate, follow up, and close tasks properly
tags: [foundation, workflow, tasks, coordination]
---

## Task Management

> Foundation skill — applies to ALL tasks you create or receive.

### Creating a Task

Every task you create must include these in the description:

1. **Why** — what triggered this task, what problem it solves
2. **What** — clear deliverable, acceptance criteria, expected output format
3. **Follow-up** — what happens after completion (who reads it, what decision it informs)
4. **Dependencies** — does this need something first? Does it block something else?

```
task_create(
  title="Research CRO market sentiment after Fed announcement",
  description="""
    WHY: CRO dropped 5% today. Need to understand if this is macro-driven or CRO-specific.
    WHAT: Research recent news, social sentiment, and correlation with BTC.
          Output a summary with: sentiment score, key drivers, and recommendation.
    FOLLOW-UP: Robin will use findings to decide whether to pause momentum strategy.
    DEPENDS ON: None.
  """,
  priority="high",
  tags=["research", "crypto", "market-analysis"]
)
```

Store the task key in memory so you can follow up:
```
memory_store(key="pending_research_cro_sentiment", value="INO-042", tags=["task-tracking"])
```

### Receiving a Task

When you pick up a task:
1. Read the full description — understand the WHY, not just the WHAT
2. Check dependencies — is everything available?
3. Acknowledge: update status to `in_progress`
4. If unclear, ask for clarification via `send_message` to the creator
5. Deliver in the format requested (JSON, research report, code PR, etc.)
6. Mark `done` with a result summary

### Following Up on Delegated Tasks

If you created a task for someone else, YOU own the follow-up:

**Periodic check** (every cycle or daily):
```
task_list(created_by="<your_name>", status="done")
```

For each completed task:
1. Read the result
2. If it was research → `research_search(tags=["relevant-tag"])` to find the report
3. Act on the findings (adjust strategy, create follow-up task, report to Boss)
4. If the result is insufficient → create a follow-up task with more specific requirements

**Stuck task detection:**
```
task_list(created_by="<your_name>", status="in_progress")
```
If a task has been `in_progress` for over 24 hours with no update:
- Check if the agent is active
- Add a comment or send a message asking for status
- If no response, consider reassigning or escalating to Boss

### Task Lifecycle

```
create → todo/backlog → in_progress → review → done
                ↑                        ↓
                └──── blocked ←──── (if issues found)
```

- **backlog**: unassigned, on mission board for any matching agent
- **todo**: assigned, waiting to start
- **in_progress**: actively being worked on
- **review**: work done, awaiting human review (for code/decisions)
- **blocked**: waiting on external dependency
- **done**: completed with result

### Priority Guide

| Priority | Response Time | Examples |
|----------|--------------|---------|
| **critical** | Immediate | Trade anomaly, system down, security issue |
| **high** | Within 1 hour | Signal scan follow-up, time-sensitive research |
| **medium** | Within 1 day | Performance review, routine analysis |
| **low** | When idle | Cleanup, optimization, nice-to-have research |

### Anti-patterns

- **Fire and forget**: creating a task and never checking the result
- **Vague tasks**: "look into CRO" — no WHY, no deliverable, no follow-up
- **Duplicate tasks**: check existing tasks before creating new ones
- **Over-delegation**: if you can do it in 2 minutes, just do it yourself
- **Missing tags**: tags drive the mission board matching — without them, no one picks it up
