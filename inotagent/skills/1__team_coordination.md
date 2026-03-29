---
name: team_coordination
description: Standup facilitation, meeting summarization, action item tracking, and blocker management
tags: [standup, meetings, coordination, action-items]
source: awesome-openclaw-agents/productivity/daily-standup, awesome-openclaw-agents/productivity/meeting-notes
---

## Team Coordination

> ~664 tokens

### Daily Standup

**Collection format (per person):**
1. What you did yesterday
2. What you're doing today
3. Any blockers?

**Standup summary template:**
```
Daily Standup — [Date]

BLOCKERS ([count]):
- [Person]: [blocker description] (Day [N])

Updates:
[Person]:
- Done: [completed work]
- Today: [planned work]
- Blocked: [blocker or "none"]

Missing: [names] (reminded)
Velocity: [X]/[Y] planned tasks completed yesterday.
```

**Blocker tracking rules:**
- Maintain a running list of active blockers with day count
- Alert when a blocker persists more than 2 days
- Suggest who can help unblock (based on task ownership/expertise)
- Track blocker resolution time for retro analysis

**Weekly team health summary:**
- Tasks completed vs planned
- Recurring blockers (same blocker 2+ weeks)
- Workload distribution (flag imbalance)
- Blocker resolution time (average, longest)

### Meeting Summarization

**Meeting notes template:**
```
Meeting Notes — [Meeting Name] ([Date])

Summary:
[One paragraph executive summary — decisions made and key outcomes]

Decisions:
1. [Decision in bold] — [brief context]
2. [Decision in bold] — [brief context]

Action Items:
| Owner | Task | Deadline |
|-------|------|----------|
| [name] | [specific task] | [date] |

Open Questions:
- [Question] (decide by [date])
- [Question] ([who] to investigate)

Next meeting: [date, time]
```

**Rules:**
- Every action item must have an owner and a deadline
- Capture decisions explicitly: "Decided: X"
- Keep summary under 1 page
- Exclude small talk and off-topic discussion
- Note who proposed controversial decisions for context

### Action Item Tracking

**Status report template:**
```
Open Action Items ([N] meetings):

Overdue:
- [Owner]: [task] (due [date]) — [N] days late

In Progress:
- [Owner]: [task] (due [date])

Completed:
- [Owner]: [task] (done [date])

Completion rate: [X]/[Y] ([%])
```

**Follow-up rules:**
- Send reminder 1 day before deadline
- Flag overdue items in next meeting prep
- Track completion rate over time (target: >80%)
- Items overdue 5+ days escalate to meeting agenda

### Meeting Prep Checklist
Before a recurring meeting:
1. Pull open action items from previous meeting
2. List overdue items that need discussion
3. Prepare agenda suggestions based on open items
4. Note who needs to present or report on what
