---
name: project_coordination
description: Risk management, timeline tracking, stakeholder communication, dependency mapping, and escalation frameworks
tags: [project-management, coordination, risk, stakeholders]
source: agency-agents/project-management/project-management-project-shepherd
---

## Project Coordination

> ~1010 tokens

### Risk Register Template

```
| ID | Risk | Likelihood | Impact | Score | Mitigation | Owner | Status |
|----|------|-----------|--------|-------|------------|-------|--------|
| R1 | [description] | H/M/L | H/M/L | [LxI] | [action] | [who] | Open/Mitigated |
```

**Risk scoring**: High=3, Medium=2, Low=1. Score = Likelihood x Impact.
- Score 6-9: Immediate action required
- Score 3-4: Monitor weekly, mitigation plan ready
- Score 1-2: Accept and monitor

### Risk Assessment Checklist

- [ ] Technical risks (integration complexity, unknown tech, performance)
- [ ] Resource risks (availability, skill gaps, single points of failure)
- [ ] External risks (vendor delays, API changes, regulatory)
- [ ] Scope risks (unclear requirements, stakeholder disagreement)
- [ ] Timeline risks (dependencies, parallel workstreams, holidays)

### Timeline Management

**Critical path method**:
1. List all tasks with duration estimates
2. Map dependencies (which tasks block which)
3. Calculate earliest start/finish for each task
4. Calculate latest start/finish working backward from deadline
5. Float = latest start - earliest start (zero float = critical path)
6. Monitor critical path tasks daily, others weekly

**Buffer rules**:
- Add 15-20% buffer to overall timeline
- Place buffers after dependency chains, not individual tasks
- Track buffer consumption — >50% consumed at <50% progress = escalate

### Dependency Tracking Template

```
| Task | Depends On | Type | Owner | Status | Risk |
|------|-----------|------|-------|--------|------|
| [task] | [blocker] | Hard/Soft | [who] | Waiting/Clear | H/M/L |
```

- **Hard dependency**: Cannot start until blocker completes
- **Soft dependency**: Can start but needs blocker for completion

### Stakeholder Communication Framework

**Identify stakeholders by role**:
- Decision makers: need summaries + decision points
- Contributors: need task details + blockers
- Informed parties: need status updates only

**Communication cadence**:
| Audience | Format | Frequency | Content |
|----------|--------|-----------|---------|
| Sponsors | Status report | Weekly | Health, risks, decisions needed |
| Team | Standup/check-in | Daily/2x week | Progress, blockers, next steps |
| Stakeholders | Summary update | Bi-weekly | Milestones, timeline, changes |

### Status Report Template

```
# Status: [Project Name] — [Date]

## Health: [GREEN / YELLOW / RED]
- Timeline: [on track / at risk / delayed]
- Scope: [stable / change pending / changed]
- Resources: [adequate / constrained / blocked]

## Completed
- [deliverable or milestone]

## Next Period
- [planned work]

## Blockers & Risks
- [issue + proposed resolution]

## Decisions Needed
- [decision + options + recommendation + deadline]
```

### Escalation Framework

**When to escalate**:
1. Blocker unresolved for >2 business days
2. Timeline slip >1 week on critical path
3. Resource conflict with no resolution path
4. Scope change requested without trade-off agreement
5. Risk score increases to 6+ with no mitigation

**Escalation format**:
```
ESCALATION: [one-line summary]
- Impact: [what happens if unresolved]
- Timeline: [when decision needed by]
- Options:
  1. [option + trade-off]
  2. [option + trade-off]
- Recommendation: [preferred option + rationale]
```

### Project Charter Checklist

- [ ] Problem statement with measurable success criteria
- [ ] Scope: deliverables, boundaries, explicit exclusions
- [ ] Stakeholders mapped (sponsor, team, informed)
- [ ] Resource requirements (people, budget, tools)
- [ ] High-level timeline with milestones
- [ ] Risk assessment (top 5 risks with mitigations)
- [ ] Communication plan by audience
- [ ] Decision-making authority defined
- [ ] Change control process agreed

### Project Health Rules

- Never commit to unrealistic timelines to satisfy stakeholders
- Track actual effort vs estimates to improve future planning
- Balance resource utilization to prevent burnout
- Escalate with solutions, not just problems
- Document all decisions and approval chains
