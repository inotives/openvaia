---
name: log_analysis
description: Parse logs at scale, detect anomalous patterns, cluster errors, and correlate events across distributed services.
tags: [devops, logs, debugging, observability]
source: awesome-openclaw-agents/agents/devops/log-analyzer
---

## Log Analysis

> ~470 tokens

### Analysis Workflow

1. Specify time window and log source
2. Calculate total events and error rate vs. baseline
3. Separate new errors (first seen today) from recurring known issues
4. Group similar errors (error clustering) to reduce noise
5. Correlate events across services to trace cascading failures
6. Provide root cause hypothesis with investigation suggestions

### Log Summary Format

```
Log Summary -- Last <time window>

Total Events: <count>
Error Rate: <rate>% (baseline: <baseline>%) -- <status since time>

New Errors (first seen today):
| Error | Service | Count | First Seen |
|-------|---------|-------|------------|

Recurring Errors (known):
| Error | Service | Count | Trend |
|-------|---------|-------|-------|

Correlation:
<explanation of relationships between errors, timeline reconstruction>

Suggested Investigation: <next steps>
```

### Error Clustering

Group similar errors together instead of listing every occurrence:

```
Cluster N (<count> occurrences):
  <error message>
  Services: <affected services>
  Pattern: <temporal pattern>
```

### Distributed Tracing Reconstruction

When errors span multiple services:
1. Identify the originating failure
2. Map the cascade timeline (which service failed first, what depended on it)
3. Reconstruct the failure chain with timestamps
4. Identify the root cause vs. symptoms

### Log Query Generation

Generate queries for common platforms:
- Elasticsearch / Kibana
- Loki / Grafana
- CloudWatch Logs Insights
- Splunk SPL

### Rules

- Always specify the time window and log source when presenting findings
- Group similar errors together instead of listing every occurrence
- Include occurrence counts ("seen 847 times in the last hour" matters more than a single example)
- Always distinguish between new errors and recurring known issues
- Report error rate changes relative to baseline
- Translate stack traces and error codes into plain language explanations
