---
name: query_optimization
description: PostgreSQL query optimization — EXPLAIN ANALYZE workflow, indexing strategies, N+1 detection, query plan reading
tags: [postgresql, optimization, indexing, performance, queries]
source: agency-agents/engineering/engineering-database-optimizer.md
---

## EXPLAIN ANALYZE Workflow

> ~1311 tokens

Run this process for any query that runs frequently or handles user-facing latency.

### Step 1: Get the Query Plan
```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) <your query>;
```

### Step 2: Read the Plan (bottom-up)
| Node Type | Meaning | Action |
|-----------|---------|--------|
| Seq Scan | Full table scan | Add index or check if table is small enough to ignore |
| Index Scan | Uses index, fetches from heap | Good for selective queries |
| Index Only Scan | Reads from index alone | Best case — no heap access |
| Bitmap Heap Scan | Index narrows rows, then heap fetch | Acceptable for moderate selectivity |
| Nested Loop | For each outer row, scan inner | Fine for small outer sets; bad for large |
| Hash Join | Builds hash table on one side | Good for large joins on equality |
| Sort | In-memory or disk sort | Check `sort_mem`; disk sort = needs more `work_mem` |

### Step 3: Red Flags to Check
- `actual rows` >> `estimated rows` -> Run `ANALYZE <table>` to update statistics
- `Seq Scan` on large table (>10k rows) with a WHERE clause -> Missing index
- `Sort Method: external merge Disk` -> Increase `work_mem` or add index to avoid sort
- `Loops: N` where N is large -> Possible N+1 pattern or missing index on join column
- `Filter: ...` removing most rows after scan -> Index the filter column

## Indexing Strategy Guide

### B-tree (default) — Use For:
- Equality (`=`) and range (`<`, `>`, `BETWEEN`) queries
- `ORDER BY` columns
- Foreign keys (always index foreign keys for JOIN performance)
```sql
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_created ON orders(created_at DESC);
```

### Composite Indexes — Column Order Matters:
- Put equality columns first, range/sort columns last
- `WHERE status = 'active' ORDER BY created_at DESC`:
```sql
CREATE INDEX idx_orders_status_created ON orders(status, created_at DESC);
```

### Partial Indexes — Index Only What Matters:
- Reduce index size by filtering out irrelevant rows
```sql
-- Only index active records
CREATE INDEX idx_users_email_active ON users(email) WHERE deleted_at IS NULL;
-- Only index published posts
CREATE INDEX idx_posts_published ON posts(published_at DESC) WHERE status = 'published';
```

### GIN Indexes — Use For:
- Full-text search (`tsvector`)
- JSONB containment queries (`@>`, `?`, `?|`)
- Array operations (`@>`, `&&`)
```sql
CREATE INDEX idx_posts_fts ON posts USING GIN(to_tsvector('english', title || ' ' || content));
CREATE INDEX idx_data_jsonb ON events USING GIN(metadata jsonb_path_ops);
```

### GiST Indexes — Use For:
- Range types, geometric data, ltree (hierarchical)
- Full-text search (smaller than GIN but slower queries)
```sql
CREATE INDEX idx_events_range ON events USING GiST(active_during);
```

## N+1 Detection and Resolution

### Symptoms
- Application makes N+1 queries (1 list query + N detail queries)
- `pg_stat_statements` shows a query with very high `calls` count but low `mean_exec_time`
- Loop pattern in EXPLAIN output with high iteration count

### Fix: Use JOINs or Aggregation
```sql
-- INSTEAD OF: SELECT * FROM posts WHERE user_id = ? (called N times)
-- USE:
SELECT
    u.id, u.email,
    COALESCE(
        json_agg(
            json_build_object('id', p.id, 'title', p.title)
        ) FILTER (WHERE p.id IS NOT NULL),
        '[]'
    ) AS posts
FROM users u
LEFT JOIN posts p ON p.user_id = u.id
WHERE u.id = ANY($1)  -- pass array of IDs
GROUP BY u.id;
```

### Fix: Batch Loading (application level)
```
1. Collect all IDs from the first query
2. Run a single IN/ANY query for related records
3. Map results back in application code
```

## Safe Migration Checklist

- [ ] Add columns with `DEFAULT` (PostgreSQL 11+ avoids table rewrite)
- [ ] Create indexes with `CONCURRENTLY` (no table lock)
- [ ] Never drop columns in the same deploy that removes code references
- [ ] Add `NOT NULL` constraints in two steps: add constraint as `NOT VALID`, then `VALIDATE CONSTRAINT`
- [ ] Always write reversible migrations (UP + DOWN)

```sql
-- Safe: non-blocking index creation
CREATE INDEX CONCURRENTLY idx_posts_view_count ON posts(view_count DESC);

-- Safe: add NOT NULL in two steps
ALTER TABLE posts ADD CONSTRAINT posts_title_not_null CHECK (title IS NOT NULL) NOT VALID;
ALTER TABLE posts VALIDATE CONSTRAINT posts_title_not_null;
```

## PostgreSQL Performance Rules

1. **Always EXPLAIN ANALYZE** before deploying new queries
2. **Index every foreign key** — JOINs without indexes cause sequential scans
3. **Avoid SELECT \*** — fetch only needed columns; enables index-only scans
4. **Use connection pooling** — never open connections per request (use PgBouncer or built-in pool)
5. **Run ANALYZE after bulk loads** — keeps planner statistics accurate
6. **Set appropriate work_mem** — per-operation sort/hash memory (default 4MB is often too low)
7. **Monitor with pg_stat_statements** — find top queries by total time, calls, and mean time
8. **Use CONCURRENTLY for index operations** — avoids locking tables in production
