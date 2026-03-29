---
name: system_design
description: System design patterns, API design principles, scaling frameworks, and database architecture choices
tags: [architecture, api, scaling, database, design]
source: agency-agents/engineering/engineering-backend-architect.md
---

## System Design Checklist

> ~918 tokens

When designing or evaluating a system, work through these layers in order.

### 1. Architecture Pattern Selection

| Pattern | Choose When | Key Trade-off |
|---------|------------|---------------|
| Monolith | Small team, fast iteration, unclear domain boundaries | Simple but harder to scale independently |
| Microservices | Clear domains, independent scaling, team autonomy | Flexible but complex operations |
| Event-driven | Async workflows, loose coupling, high throughput | Decoupled but eventual consistency |
| Serverless | Bursty traffic, minimal ops budget | Auto-scales but cold starts and vendor lock-in |
| Hybrid | Core monolith + extracted hot paths | Balanced but two operational models |

### 2. Service Decomposition Template

For each service, define:
- **Database**: Engine, replication strategy, encryption
- **APIs**: Protocol (REST/GraphQL/gRPC), versioning scheme
- **Events**: Published events, consumed events, ordering guarantees
- **Cache**: Strategy (write-through, write-behind, cache-aside), TTL, invalidation
- **Scaling**: Stateless? Horizontal trigger (CPU/queue depth/latency)?

### 3. API Design Principles

- Version APIs from day one (`/api/v1/`)
- Return structured errors: `{ "error": "<message>", "code": "<MACHINE_READABLE>" }`
- Include metadata in responses: `{ "data": {...}, "meta": { "timestamp": "..." } }`
- Apply rate limiting per client (e.g., 100 req/15min window)
- Use pagination for list endpoints (cursor-based preferred over offset)
- Validate input at the boundary; never trust client data

### 4. Database Architecture Decisions

- **UUID vs BIGSERIAL**: UUID for distributed systems, BIGSERIAL for single-database
- **Soft delete** (`deleted_at TIMESTAMPTZ NULL`): Use when audit trail needed; add `WHERE deleted_at IS NULL` to indexes
- **Partial indexes**: Index only active/relevant rows to reduce index size
- **Full-text search**: Use `GIN(to_tsvector(...))` for PostgreSQL text search
- **Constraints**: Enforce `CHECK` constraints at DB level, not just app level
- **Timestamps**: Always use `TIMESTAMPTZ`, never `TIMESTAMP`

### 5. Reliability Checklist

- [ ] Circuit breakers on all external service calls
- [ ] Retry with exponential backoff + jitter
- [ ] Graceful degradation (serve stale cache if DB is down)
- [ ] Health check endpoints (liveness + readiness)
- [ ] Connection pooling configured (not per-request connections)
- [ ] Timeouts set on all network calls
- [ ] Idempotency keys on write operations

### 6. Caching Strategy Decision Tree

1. Is the data read-heavy (>10:1 read:write)? -> Consider caching
2. Can you tolerate stale data? -> Yes: TTL-based cache. No: Write-through or skip cache
3. Is the working set small enough to fit in memory? -> Yes: In-process cache. No: Redis/external cache
4. Multiple instances? -> Use external cache (Redis) to avoid inconsistency

### 7. Scaling Decision Framework

- **Vertical first**: Cheaper, simpler. Upgrade until cost/diminishing returns hit
- **Horizontal when**: Single instance can't handle load, need fault tolerance, or need geo-distribution
- **Stateless services**: Required for horizontal scaling. Move state to DB/cache/object store
- **Read replicas**: When read load >> write load
- **Sharding**: Last resort. Adds complexity to queries, joins, migrations

### 8. Security Defaults

- Encrypt at rest (DB-level or disk encryption) and in transit (TLS)
- Least privilege for all service accounts and DB roles
- No secrets in code or env files committed to git
- Auth: OAuth 2.0 / JWT with short expiry + refresh tokens
- Input validation + parameterized queries (never string concatenation for SQL)
- Rate limiting on all public endpoints
- Audit logging for sensitive operations
