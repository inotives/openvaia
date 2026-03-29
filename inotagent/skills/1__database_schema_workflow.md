---
name: database_schema_workflow
description: Safe database migration workflow using dbmate and dev schema
tags: [database, migration]
source: openvaia/v1-migration-seed
---

## Database Schema Workflow

> ~340 tokens
When a task involves creating or modifying database tables:
1. **Never run migrations against the live schema directly**
2. Snapshot the live schema structure into a `_dev` copy:
   ```bash
   /app/scripts/schema_dev.sh snapshot <schema_name>
   ```
   This creates `<schema_name>_dev` with the same structure (no data).
3. Write the dbmate migration file in `infra/postgres/migrations/`:
   ```sql
   -- migrate:up
   ALTER TABLE schema_name.table ADD COLUMN ...;

   -- migrate:down
   ALTER TABLE schema_name.table DROP COLUMN ...;
   ```
4. Test the migration against `_dev`:
   ```bash
   /app/scripts/schema_dev.sh test <schema_name> <migration_file>
   ```
   This runs the up migration, verifies it, then runs the down migration to confirm rollback works.
5. Clean up the `_dev` schema:
   ```bash
   /app/scripts/schema_dev.sh cleanup <schema_name>
   ```
6. Commit the migration file, push, and raise a PR
7. The migration runs on the live schema at next deployment

**Rules:**
- Always include both `-- migrate:up` and `-- migrate:down` sections
- Test both up and down migrations before committing
- Never modify existing migration files that have already been deployed
- For destructive changes (drop column, drop table), confirm with Boss first
