---
name: sla_monitoring
description: Track uptime, latency, and error budgets against SLA targets with projected breach timelines.
tags: [devops, sla, monitoring, reliability]
source: awesome-openclaw-agents/agents/devops/sla-monitor
---

## SLA Monitoring

> ~568 tokens

### Key Metrics to Track

| Metric | Description | Precision |
|--------|-------------|-----------|
| Uptime % | Availability against SLA target | 4 decimal places (e.g., 99.9712%) |
| Error budget | Remaining allowed downtime in period | Minutes remaining |
| P50 latency | Median response time | ms |
| P95 latency | 95th percentile response time | ms |
| P99 latency | 99th percentile response time | ms |

### Common SLA Targets

| Target | Monthly Downtime Allowed |
|--------|-------------------------|
| 99.9% | 43.8 minutes |
| 99.95% | 21.9 minutes |
| 99.99% | 4.4 minutes |

### Error Budget Calculation

```
Monthly budget (minutes) = (1 - SLA target) x 43,200 minutes
Budget consumed = total downtime minutes this period
Budget remaining = monthly budget - budget consumed
Budget burn rate = budget consumed / days elapsed
Projected depletion = budget remaining / daily burn rate
```

### SLA Report Format

```
SLA Report -- <service> (<period>)

Uptime: <percentage> against <target> SLA
Downtime: <minutes> (budget: <allowed minutes>)
Error budget consumed: <percent>%
Error budget remaining: <minutes> min (<days> days at current rate)

Incidents contributing to downtime:
- <date> <incident> (<duration>)

Latency:
- P50: <value>ms (threshold: <threshold>ms)
- P95: <value>ms (threshold: <threshold>ms)
- P99: <value>ms (threshold: <threshold>ms)

Status: ON TRACK / AT RISK / BREACHED
Recommendation: <action if at risk>
```

### Multi-Service Comparison Format

```
Trailing 30-day SLA comparison:
| Service | Uptime | Target | Error Budget | Status |
|---------|--------|--------|-------------|--------|
```

### Alert Rules

- Always show both current period and trailing 30-day metrics
- Error budget calculations must account for remaining days in the period
- Never round metrics in a favorable direction; always round toward the worse case
- Include actionable recommendations with every alert
- Create issues automatically when error budget drops below 25%
- Alert on degradation patterns before they become SLA breaches
