---
name: etl_pipeline
description: Design, monitor, and troubleshoot ETL data pipelines with validation at every step.
tags: [data, etl, pipeline, orchestration]
source: awesome-openclaw-agents/agents/data/etl-pipeline
---

## ETL Pipeline

> ~572 tokens

### Pipeline Design Workflow

1. **Extract:** Define source systems, API endpoints, or database tables. Choose incremental vs. full load strategy.
2. **Transform:** Define transformation logic (flatten, join, convert, aggregate). Generate in SQL, Python, or dbt.
3. **Load:** Define target schema. Choose insert/upsert/replace strategy.
4. **Validate:** Define row count checks, null rate thresholds, schema drift detection.
5. **Schedule:** Define run frequency and orchestration dependencies.

### Pipeline Specification Template

```
Pipeline: <name>
Schedule: Every <interval>
Source: <system/API/table>
Target: <schema.table>

Extract:
- Method: <API call / DB query / file read>
- Incremental key: <timestamp column>
- Expected rows/run: ~<count>

Transform:
- <step 1 description>
- <step 2 description>

Load:
- Strategy: <insert / upsert / replace>
- Key: <primary/unique key>

Validation:
- Row count: match source or within <threshold>%
- Null rate on <column>: < <threshold>%
- Schema: <expected columns>
```

### Pipeline Run Logging

Every pipeline run must record:
- Start time, end time, duration
- Row counts (extracted, transformed, loaded)
- Error details (if any)
- Stage where failure occurred

### Failure Diagnosis Template

```
Pipeline: <name>
Failed at: <timestamp>
Stage: <Extract / Transform / Load>
Error: <message>

Source row count: <N>
Last successful run: <timestamp> (<N> rows)

Root cause: <explanation>
Fix options:
1. <option with trade-offs>
2. <option with trade-offs>
```

### Validation Checks

| Check | When | Action on Failure |
|-------|------|-------------------|
| Row count | After load | Alert if delta > threshold |
| Null rate | After transform | Block load if above threshold |
| Schema drift | Before transform | Alert and log new/missing columns |
| Data freshness | After load | Alert if source data is stale |
| Duplicate check | After load | Alert and deduplicate |

### Rules

- Log every pipeline run with row counts, duration, and error details
- Never overwrite production tables without backup confirmation
- Validate at every stage (extract, transform, load)
- Use incremental loads where possible to minimize processing time
- Include rollback strategy for failed loads
