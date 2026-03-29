# Curated Resources Registry — Execution Plan

## Backstory

When agents research a topic, they often waste iterations trying unreliable APIs, hitting paywalls, or crawling sites that return garbage HTML. For example, Ino might try 5 different crypto data APIs before landing on GeckoTerminal — which we already know works well. Next time a similar question comes up, the agent starts from scratch again because there's no shared knowledge of which sources are good.

Meanwhile, the team accumulates implicit knowledge about reliable sources: "Birdeye needs a paid key", "GeckoTerminal is free and reliable for Solana", "DeFiLlama has the best TVL data". This knowledge lives in human memory or scattered across agent conversation history — not in a structured, searchable place.

## Purpose

Add a **resources registry** — a Postgres table of curated URLs, APIs, and data sources tagged by topic. Agents check this registry first when researching, using matching tags to find relevant sources before falling back to general web search. This reduces wasted LLM iterations and improves research quality.

Resources have a status lifecycle similar to skills: humans can add trusted sources directly, and agents can propose new sources as drafts based on their evaluation of a site's usefulness during research.

## How It Works

### Agent Research Flow (with resources)

```
Agent receives research task (e.g., "find Solana DEX volumes")
        ↓
Agent calls resource_search(tags=["solana", "dex", "crypto"])
        ↓
Returns matching resources:
  - GeckoTerminal API (free, no auth)     — https://api.geckoterminal.com/...
  - DeFiLlama API (free, no auth)         — https://api.llama.fi/...
  - Raydium API (free, sometimes stale)   — https://api.raydium.io/...
        ↓
Agent uses these sources FIRST
        ↓
If not enough → falls back to general web search (browser tool)
```

### Agent Proposing New Resources

```
During research, agent finds a useful new source
        ↓
Agent calls resource_add(
    url="https://api.jupiter.ag/v1/...",
    name="Jupiter Aggregator API",
    description="Solana DEX aggregator — free, real-time swap routes and prices",
    tags=["solana", "dex", "crypto", "api"],
    notes="No auth required. JSON responses. Rate limit ~60 req/min.",
    status="draft"
)
        ↓
Draft resource appears in Admin UI with "draft" badge
        ↓
Human reviews — approve, edit, or reject
        ↓
Approved resources available to all agents
```

---

## Technical Design

### Database Table

```sql
CREATE TABLE platform.resources (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    tags TEXT[] DEFAULT '{}',
    notes TEXT,                              -- usage tips, rate limits, auth requirements
    priority INTEGER NOT NULL DEFAULT 50     -- 1-100, higher = more reliable. Default 50, human adjustable.
        CHECK (priority BETWEEN 1 AND 100),
    status VARCHAR(16) NOT NULL DEFAULT 'active'
        CHECK (status IN ('draft', 'active', 'rejected', 'inactive')),
    created_by VARCHAR(64),                  -- agent name or NULL for human-created
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_resources_tags ON platform.resources USING GIN (tags);
CREATE INDEX idx_resources_status ON platform.resources (status);
```

### Tools

Two new tools:

**`resource_search`** — Find relevant resources by tags
```python
{
    "name": "resource_search",
    "description": "Search curated resources by tags. Use before general web search to find reliable sources first.",
    "input_schema": {
        "type": "object",
        "properties": {
            "tags": {"type": "array", "items": {"type": "string"}, "description": "Topic tags to match"},
            "query": {"type": "string", "description": "Optional keyword search in name/description"},
        },
    },
}
```

Returns only `active` resources, ordered by `priority` descending (highest first). Matches via tag overlap (`&&` operator) and optional keyword FTS.

**`resource_add`** — Propose a new resource (always created as draft)
```python
{
    "name": "resource_add",
    "description": "Propose a new curated resource. Created as draft — requires human approval before other agents can use it.",
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Resource URL"},
            "name": {"type": "string", "description": "Short name"},
            "description": {"type": "string", "description": "What this resource provides"},
            "tags": {"type": "array", "items": {"type": "string"}, "description": "Topic tags"},
            "notes": {"type": "string", "description": "Usage tips, rate limits, auth info"},
        },
        "required": ["url", "name", "description", "tags"],
    },
}
```

### Admin UI

Add a **Resources** page (or tab under an existing page):

- Table: name, URL, tags, priority, status, created_by, notes
- Priority column: sortable, editable inline (slider or number input, 1-100)
- Tag filter dropdown + keyword search
- Add/Edit modal for humans to create resources directly (status: `active`)
- Approve/Reject buttons for draft resources
- Status badges: draft (orange), active (green), rejected (red), inactive (grey)

### Seeding Initial Resources

The migration seeds known good resources from current agent experience:

```sql
INSERT INTO platform.resources (url, name, description, tags, notes, priority, status) VALUES
    ('https://api.geckoterminal.com/api/v2', 'GeckoTerminal API', 'DEX pool data, token prices, volume — free, no auth', ARRAY['crypto', 'dex', 'solana', 'ethereum', 'api'], 'Rate limit ~30 req/min. JSON responses.', 50, 'active'),
    ('https://api.llama.fi', 'DeFiLlama API', 'TVL, yields, protocol data across all chains — free, no auth', ARRAY['crypto', 'defi', 'tvl', 'yield', 'api'], 'Comprehensive. No rate limit documented.', 50, 'active'),
    ('https://api.coingecko.com/api/v3', 'CoinGecko API', 'Token prices, market data, historical — free tier available', ARRAY['crypto', 'market', 'price', 'api'], 'Free tier: 10-30 req/min. Pro key for higher limits.', 50, 'active')
ON CONFLICT DO NOTHING;
```

---

## Development Steps

### Step 1: Migration — resources table + seed data

**File**: `infra/postgres/migrations/YYYYMMDD_add_resources.sql`

- Create `resources` table with indexes
- Seed known good resources
- Add config entry for resource feature

Estimated: ~30 lines

### Step 2: DB layer

**File**: `inotagent/src/inotagent/db/resources.py` (new)

- `search_resources(tags, query)` — returns active resources matching tags/keywords
- `add_resource(url, name, description, tags, notes, created_by)` — insert as draft

Estimated: ~40 lines

### Step 3: Tool handlers

**File**: `inotagent/src/inotagent/tools/research.py` (extend existing)

- Add `resource_search` and `resource_add` tool definitions and handlers
- Or create a new `inotagent/src/inotagent/tools/resources.py`

Estimated: ~50 lines

### Step 4: Register tools

**File**: `inotagent/src/inotagent/tools/setup.py`

- Register `resource_search` and `resource_add`

Estimated: ~5 lines

### Step 5: Admin UI — Resources page

**File**: `ui/src/app/resources/page.tsx` (new)

- Table with name, URL, tags, priority, status, created_by, notes
- Tag filter + search
- Add/Edit modal
- Approve/Reject for drafts

**File**: `ui/src/app/api/resources/route.ts` (new)

- GET: list resources (filterable by status, tags)
- POST: create resource (human-created, status: active)

**File**: `ui/src/app/api/resources/[id]/route.ts` (new)

- PUT: update resource
- PATCH: update status (approve/reject)
- DELETE: remove resource

**File**: `ui/src/components/AppLayout.tsx`

- Add "Resources" to sidebar navigation

Estimated: ~150 lines

### Step 6: Tests

**File**: `inotagent/tests/test_tools.py`

- Test resource_search returns only active resources
- Test resource_search tag matching
- Test resource_add creates with status='draft' and created_by=agent_name

**File**: `tests/test_ui.py`

- Test resource API endpoints

Estimated: ~40 lines

---

## Summary

| Component | File(s) | Lines |
|---|---|---|
| Migration + seed data | `infra/postgres/migrations/` | ~30 |
| DB layer | `db/resources.py` | ~40 |
| Tool handlers | `tools/resources.py` | ~50 |
| Register tools | `tools/setup.py` | ~5 |
| Admin UI (page + API) | `ui/src/app/resources/` + `AppLayout.tsx` | ~150 |
| Tests | `test_tools.py` + `test_ui.py` | ~40 |
| **Total** | | **~315 lines** |

One migration. Two new tools. One new UI page. No new dependencies.

---

## Future Enhancements

- **Resource reliability scoring** — track how often agents successfully use each resource (success/fail ratio)
- **Auto-tag from usage** — when an agent uses a resource in a specific context, auto-suggest additional tags
- **Resource health check** — periodic cron to ping resource URLs and flag dead/changed endpoints
- **Per-agent resource preferences** — agents can "favorite" resources they find most useful
- **Resource embedding** — embed resource descriptions for semantic search (e.g., "where can I find liquidity data?" matches DeFiLlama)


## Status: DONE
