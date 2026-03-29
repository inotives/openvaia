---
name: deployment_monitoring
description: Monitor CI/CD pipelines, track deployment health, enforce policies, and report infrastructure metrics.
tags: [devops, deployment, monitoring, infrastructure]
source: awesome-openclaw-agents/agents/devops/deploy-guardian + infra-monitor
---

## Deployment Monitoring

> ~656 tokens

### Deployment Tracking

For every deployment, record:
- Commit SHA and author
- Service name and target environment
- Status (deployed, failed, pending approval, rolled back)
- Timestamp
- Failure details if applicable

### Post-Deploy Health Check

After every production deployment, monitor:

| Metric | Check | Alert Threshold |
|--------|-------|-----------------|
| Error rate | Compare to baseline | > 2x baseline |
| P99 latency | Compare to baseline | > 20% increase |
| CPU usage | Compare to baseline | > 80% |
| Memory usage | Compare to baseline | > 85% |

**Rollback Decision:** If error rate or latency exceeds threshold for >5 minutes, recommend rollback.

### DORA Metrics

Track these deployment performance metrics:
- **Deployment Frequency:** How often code deploys to production
- **Lead Time:** Commit to production time
- **MTTR:** Mean time to restore service after failure
- **Change Failure Rate:** Percentage of deploys causing incidents

### Deployment Policy Enforcement

- Enforce freeze windows (no deploys during blackout periods)
- Require approval gates for production deploys
- Define canary thresholds before full rollout
- Block deploys that violate policies

### Infrastructure Health Monitoring

Track per node/container:

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| CPU | < 60% | 60-80% | > 80% |
| Memory | < 70% | 70-85% | > 85% |
| Disk | < 75% | 75-90% | > 90% |

### Monitoring Rules

- Report trends, not just snapshots ("disk at 82% and growing 2%/day")
- Prioritize alerts by business impact, not just technical severity
- Always suggest a remediation action alongside any alert
- Include time window when reporting metrics
- Track container orchestration status (pod restarts, OOMKills)
- Predict capacity issues from historical trends

### Deploy Status Report Format

```
Deploy Status -- <date>

| # | Service | Env | Status | Time | Author |
|---|---------|-----|--------|------|--------|

Failure Details (if any):
- Step: <failed step>
- Error: <message>
- Commit: <sha> -- <description>
- Action Needed: <remediation>
```

### Infrastructure Health Report Format

```
Infrastructure Health -- <date>

| Node | CPU | Memory | Disk | Status |
|------|-----|--------|------|--------|

Alerts:
1. <node> <metric> at <value> -- trending <direction>. Recommend: <action>.

Kubernetes Pods:
- Running: X/Y
- CrashLoopBackOff: N (<names>)
- OOMKilled today: N
```
