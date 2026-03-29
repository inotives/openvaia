---
name: database_migration
description: Database migration planning with zero-downtime strategies and rollback procedures
tags: [development, database, migration, devops]
source: awesome-openclaw-agents/development/migration-helper
---

## Database Migration

> ~529 tokens

### Migration Planning Workflow

1. **Assess** — Understand the change: schema alter, data migration, or both?
2. **Size check** — How many rows in affected tables? This determines strategy.
3. **Write UP migration** — The forward migration script
4. **Write DOWN migration** — The rollback script (mandatory before proceeding)
5. **Test** — Run on a copy of production data, verify row counts and integrity
6. **Execute** — Apply in production with monitoring
7. **Validate** — Verify row counts, checksums, and application behavior post-migration

### Zero-Downtime Strategies

**Adding a column (any table size)**
- PostgreSQL 11+: `ALTER TABLE ADD COLUMN ... DEFAULT` is instant (no table rewrite)
- Always add as nullable or with a default — never add NOT NULL without a default on a large table

**Backfilling data**
- Run in batches (10K-50K rows per batch) to avoid long locks
- Use `WHERE id BETWEEN x AND y` or cursor-based batching
- Estimate time: measure one batch, multiply by total batches

**Adding an index**
- Use `CREATE INDEX CONCURRENTLY` (PostgreSQL) to avoid locking the table
- This takes longer but does not block reads or writes

**Renaming a column**
- Do NOT use `ALTER TABLE RENAME COLUMN` on live systems
- Instead: add new column, dual-write, backfill, switch reads, drop old column

**Dropping a column**
- First remove all code references, deploy
- Then drop the column in a separate migration

### Validation Checklist

- [ ] Row count before and after matches (or expected delta documented)
- [ ] Application can read/write to the changed schema
- [ ] Rollback script tested and confirmed working
- [ ] No long-running locks during migration (check `pg_stat_activity`)
- [ ] Indexes created and query performance verified

### Framework Upgrade Workflow

1. Read the changelog and breaking changes list for every version between current and target
2. Search the codebase for usage of deprecated or changed APIs
3. Estimate effort per breaking change
4. Branch, migrate one file/route at a time, test each
5. Run full test suite before merging
