---
name: data_quality
description: Profile datasets, detect duplicates/nulls/outliers, standardize formats, and generate data quality reports.
tags: [data, quality, cleaning, profiling]
source: awesome-openclaw-agents/agents/data/data-cleaner
---

## Data Quality

> ~500 tokens

### Data Profiling Checklist

For every dataset, assess:
- **Completeness:** Null counts and percentages per column
- **Uniqueness:** Duplicate detection on key columns
- **Format consistency:** Date formats, phone numbers, addresses, currencies
- **Outliers:** Statistical outliers and impossible values
- **Distribution:** Value distribution stats per column

### Data Cleaning Workflow

1. Profile the dataset (completeness, uniqueness, distributions)
2. Detect duplicates (exact match and fuzzy matching)
3. Identify format inconsistencies
4. Flag outliers and impossible values
5. Apply standardizations (dates to ISO 8601, phones to E.164, etc.)
6. Generate cleaned copy with transformation log
7. Produce data quality report with severity-ranked issues

### Common Issues and Fixes

| Issue | Detection | Fix |
|-------|-----------|-----|
| Duplicate records | Exact + fuzzy matching on key fields | Deduplicate, keep most recent |
| Inconsistent dates | Multiple format detection | Standardize to ISO 8601 |
| Phone format variations | Pattern matching (+1, 001, no prefix) | Standardize to E.164 |
| Null/missing values | Null count per column | Flag for review or apply defaults |
| Outliers | Statistical analysis (z-score, IQR) | Flag for manual review |
| Encoding issues | Character detection | Convert to UTF-8 |

### Data Quality Report Format

```
Data Quality Report -- <table/file> (<row count> rows)

Completeness: <percent>%
Nulls per column:
- <column>: <count> (<percent>%)

Duplicates: <count> on <key column>
- Exact: <count>
- Fuzzy: <count>

Format Issues:
- <column>: <description>

Outliers:
- <count> rows with <description>

Recommendations:
1. <prioritized action>
```

### Rules

- Never delete original data -- create cleaned copies with a transformation log
- Flag but do not auto-fix ambiguous values (ask for clarification)
- Document every transformation so changes are auditable and reversible
- Include severity ranking for each issue found
