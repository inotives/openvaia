---
name: incident_response
description: Triage production incidents, coordinate response, write runbooks, and generate post-mortems.
tags: [devops, incident, sre, runbook]
source: awesome-openclaw-agents/agents/devops/incident-responder + runbook-writer
---

## Incident Response

> ~645 tokens

### Severity Classification

| Severity | Criteria | Response Time |
|----------|----------|---------------|
| SEV1 | Production down, data loss, security breach | Immediate, all-hands |
| SEV2 | Customer-facing, revenue-impacting | < 15 minutes |
| SEV3 | Degraded service, workaround available | < 1 hour |
| SEV4 | Minor issue, no user impact | Next business day |

### Incident Triage Workflow

1. Acknowledge the alert immediately
2. Classify severity based on impact and blast radius
3. Assign roles: Incident Commander, Comms Lead, Engineering Lead
4. Correlate with recent deploys and dependency changes
5. Determine immediate actions (rollback, scale, failover)
6. Notify stakeholders with appropriate detail level
7. Track timeline of events and actions

### Runbook Template

Every runbook must include:

```
Title: <descriptive name>
Severity: <P1/P2/P3>
ETA: <estimated resolution time>
Symptoms: <what you will observe>

Prerequisites:
- <access requirements>
- <tools needed>

Procedure:
1. <step with exact CLI command>
   Verify: <how to confirm this step worked>
2. <next step>
   Verify: <verification>

Rollback Plan:
- <steps to undo if things go wrong>

Escalation Path:
- If not resolved in <time>, page <team/person>
```

### Runbook Rules

- Number every step; never use prose paragraphs for procedures
- Include exact CLI commands with placeholder values marked as `<PLACEHOLDER>`
- Add verification checks after every critical step
- Include time estimates for each section

### Post-Incident Report Template

```
## Post-Incident Report -- <Title>

Duration: <start> - <end> (<total time>)
Severity: <level>
Impact: <quantified user/business impact>

### Timeline
- <time> -- <event>
- <time> -- <action taken>
- <time> -- <resolution>

### Root Cause
<clear explanation of what failed and why>

### Action Items
- [ ] <preventive measure with owner>
- [ ] <monitoring improvement>
- [ ] <process change>
```

### Communication Guidelines

- **Technical audience:** Include logs, metrics, and specific error messages
- **Executive audience:** Focus on impact, duration, resolution status, and prevention plan
- Inform stakeholders at every severity change
- Always recommend a post-mortem, even for minor incidents

### Rules

- Classify severity before taking any remediation action
- Never skip the communication step
- Keep responses concise unless asked for detail
- Always recommend rollback criteria before a deploy starts
- Report failures within 60 seconds of detection
