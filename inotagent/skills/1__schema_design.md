---
name: schema_design
description: Design normalized database schemas from requirements, generate migrations, suggest indexes, and detect anti-patterns.
tags: [development, database, schema, postgresql]
source: awesome-openclaw-agents/agents/development/schema-designer
---

## Schema Design

> ~451 tokens

### Design Workflow

1. Gather requirements in plain language
2. Identify entities and relationships
3. Normalize to 3NF by default (denormalize only when justified by performance)
4. Define primary keys, foreign keys, and constraints
5. Suggest indexes based on expected query patterns
6. Generate SQL DDL and Mermaid ERD diagram
7. Produce migration files (SQL, Prisma, Drizzle, TypeORM) as needed

### Table Design Rules

- Every table must have a primary key, `created_at`, and `updated_at`
- Use `snake_case` for column names
- Use singular nouns for table names
- Always include foreign key constraints and `ON DELETE` behavior
- Default to PostgreSQL syntax unless specified otherwise

### Anti-Patterns to Detect

- **God tables:** Single table with too many columns covering multiple concerns
- **Polymorphic associations:** Foreign key pointing to multiple tables via type column
- **EAV abuse:** Entity-Attribute-Value pattern used where a proper schema is better
- **Missing indexes:** Columns used in WHERE/JOIN without indexes
- **Missing constraints:** No foreign keys, no NOT NULL where appropriate

### Index Strategy

- Add indexes for columns used in WHERE clauses and JOINs
- Consider composite indexes for multi-column queries
- Add unique constraints where business logic requires uniqueness
- Use partial indexes for filtered queries (e.g., `WHERE status = 'active'`)

### Schema Change Workflow

1. Describe the change needed
2. Generate migration SQL with `ALTER TABLE` statements
3. Include rollback plan
4. Validate foreign key and constraint integrity
5. Update ERD to reflect changes

### Output Format

Every schema response should include:
- SQL DDL statements
- Mermaid ERD diagram
- Index recommendations with rationale
- Notes on denormalization trade-offs (if applicable)
