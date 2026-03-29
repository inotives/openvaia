---
name: report_format
description: Structured markdown format for research reports
tags: [reporting, research]
source: openvaia/v1-migration-seed
---

## Report Format

> ~174 tokens
Use markdown for all reports -- suitable for DB storage, Discord, and file output.

```
# [Topic] -- Research Report
Date: YYYY-MM-DD | Task: <task_key> | Researcher: ino

## Summary
- 3-5 bullet points with key findings

## Background
Brief context on why this was researched

## Findings
Detailed findings with data, tables, links

## Recommendations
What to do next -- actionable items for Boss or peer agents

## Sources
Links to docs, APIs, articles referenced
```

Keep reports concise. For Discord, post only the Summary section -- link to the full report.
