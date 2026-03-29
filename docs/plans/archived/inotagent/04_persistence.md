# Phase 4: Persistence & Memory

**Goal**: Conversation history persists across restarts. Context window is managed automatically. Agent has semantic memory search.

**Delivers**: Agent remembers previous conversations, handles long contexts without crashing, and can search its own memory for relevant information.

**Complexity**: Medium

## Dependencies

- Phase 1 (Foundation) — agent loop, config
- Phase 3 (Channels) — conversation IDs and channel types from connectors

## What to build

### 4.1 Async Postgres connection pool (`db/pool.py`)

Replace sync `psycopg2` with async `psycopg` (v3):

```python
import psycopg_pool

_pool: psycopg_pool.AsyncConnectionPool | None = None

async def init_pool():
    global _pool
    _pool = psycopg_pool.AsyncConnectionPool(
        conninfo=f"host={POSTGRES_HOST} port={POSTGRES_PORT} dbname={POSTGRES_DB} user={POSTGRES_USER} password={POSTGRES_PASSWORD}",
        min_size=2,
        max_size=10,
    )
    await _pool.open()

async def get_connection():
    return _pool.connection()

async def close_pool():
    if _pool:
        await _pool.close()
```

### 4.2 Conversation history (`db/conversations.py`)

Store and retrieve message history per conversation:

```python
async def save_message(conversation_id: str, role: str, content: str, channel_type: str = "cli", tool_calls: list | None = None, metadata: dict | None = None):
    """Save a message to conversation history."""
    async with get_connection() as conn:
        await conn.execute(
            f"""INSERT INTO {SCHEMA}.conversations
                (conversation_id, role, content, channel_type, tool_calls, metadata, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())""",
            (conversation_id, role, content, channel_type, json.dumps(tool_calls), json.dumps(metadata)),
        )

async def load_history(conversation_id: str, limit: int = 100) -> list[LLMMessage]:
    """Load recent messages for a conversation."""
    async with get_connection() as conn:
        rows = await conn.execute(
            f"""SELECT role, content, tool_calls, metadata
                FROM {SCHEMA}.conversations
                WHERE conversation_id = %s
                ORDER BY created_at DESC
                LIMIT %s""",
            (conversation_id, limit),
        ).fetchall()
    return [row_to_message(r) for r in reversed(rows)]

async def list_conversations(agent_name: str, limit: int = 20) -> list[dict]:
    """List recent conversations with last message preview."""
```

**New migration** for conversations table:

```sql
CREATE TABLE IF NOT EXISTS ${SCHEMA}.conversations (
    id BIGSERIAL PRIMARY KEY,
    conversation_id VARCHAR(128) NOT NULL,
    agent_name VARCHAR(64) NOT NULL,
    role VARCHAR(16) NOT NULL,           -- user, assistant, tool
    content TEXT,
    channel_type VARCHAR(16) NOT NULL DEFAULT 'cli',  -- discord, slack, whatsapp, cli, cron
    tool_calls JSONB,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conversations_lookup
    ON ${SCHEMA}.conversations (conversation_id, created_at);
CREATE INDEX idx_conversations_agent
    ON ${SCHEMA}.conversations (agent_name, created_at DESC);
CREATE INDEX idx_conversations_channel
    ON ${SCHEMA}.conversations (channel_type, created_at DESC);
```

### 4.3 Context window management (`llm/tokens.py`)

Prevent exceeding model context limits:

```python
def build_context(
    system: str,
    history: list[LLMMessage],
    tools: list[dict],
    model_config: ModelConfig,
    reserve_output: int | None = None,
) -> list[LLMMessage]:
    """Truncate history to fit within context window.

    Strategy:
    1. System prompt + tool defs are always included (fixed cost)
    2. Most recent messages are kept (sliding window)
    3. Oldest messages are dropped first
    4. Reserve tokens for model output
    """
    max_context = model_config.context_window
    output_reserve = reserve_output or model_config.max_tokens

    available = max_context - output_reserve
    fixed_cost = count_tokens(system, model_config.id) + estimate_tools_tokens(tools)
    budget = available - fixed_cost

    # Keep messages from newest to oldest until budget exhausted
    kept = []
    used = 0
    for msg in reversed(history):
        msg_tokens = count_tokens_message(msg, model_config.id)
        if used + msg_tokens > budget:
            break
        kept.insert(0, msg)
        used += msg_tokens

    return kept
```

### 4.4 Tool result truncation

Tool results are the biggest token cost. A single `opencode run` can return 10K+ tokens. Without truncation, history fills up fast.

```python
MAX_TOOL_RESULT_CHARS = 2000  # ~500 tokens

def truncate_tool_result(result: str) -> str:
    """Truncate tool output before storing in conversation history."""
    if len(result) <= MAX_TOOL_RESULT_CHARS:
        return result
    # Keep first and last portions, drop middle
    half = MAX_TOOL_RESULT_CHARS // 2
    return (
        result[:half]
        + f"\n\n... [{len(result) - MAX_TOOL_RESULT_CHARS} chars truncated] ...\n\n"
        + result[-half:]
    )
```

Applied at two levels:

1. **Before storing** — tool results are truncated when saved to `conversations` table. Full output is never re-sent on future turns.
2. **Old turns collapsed** — when loading history, tool call messages from past turns are replaced with a summary:

```python
def collapse_old_tool_calls(history: list[LLMMessage], keep_recent: int = 2) -> list[LLMMessage]:
    """For messages older than the last N turns, replace tool results
    with a one-line summary. Keeps recent tool results intact for context."""
    # Recent turns: keep full tool results (agent needs the context)
    # Older turns: "tool:opencode → [completed, 3847 chars output]"
```

**Token budget per request:**

| Component | Tokens | Notes |
|-----------|--------|-------|
| System prompt (AGENTS.md + TOOLS.md rules) | ~2-3K | Fixed |
| Tool definitions (function calling schema) | ~1-2K | Fixed, required by API |
| Conversation history | ~5-15K | Sliding window, old turns collapsed |
| Output reserve | ~4-16K | Depends on model max_tokens |
| **Total per request** | ~12-36K | Well within 128-200K context windows |

### 4.5 Conversation pruning

Automatically clean up old conversations:

```python
async def prune_conversations(retention_days: int = 30):
    """Delete conversations older than retention period."""
    async with get_connection() as conn:
        await conn.execute(
            f"DELETE FROM {SCHEMA}.conversations WHERE created_at < NOW() - INTERVAL '%s days'",
            (retention_days,),
        )
```

### 4.6 Memory storage (`db/memory.py`)

Tag-based + full-text keyword search. No embedding model required.

```python
async def store_memory(agent_name: str, content: str, tags: list[str], tier: str = "short"):
    """Store a memory with tags and tier.

    tier: 'short' (auto-pruned after 30 days) or 'long' (kept forever)
    """
    async with get_connection() as conn:
        await conn.execute(
            f"""INSERT INTO {SCHEMA}.memories
                (agent_name, content, tags, tier, created_at)
                VALUES (%s, %s, %s, %s, NOW())""",
            (agent_name, content, tags, tier),
        )

MAX_MEMORY_CHARS = 8000  # ~2000 tokens hard cap per search call

async def search_memory(
    agent_name: str,
    query: str | None = None,
    tags: list[str] | None = None,
    days: int = 30,
) -> list[dict]:
    """Search memories by tags and/or keywords.

    Limits:
    - Time window: last N days (default 30, max 90)
    - Token cap: results capped at ~2000 tokens (8000 chars)
    - Fetch up to 20 candidates, trim by char budget

    Search modes:
    - Tags: exact match using array overlap (&&)
    - Keywords: Postgres full-text search (to_tsvector/plainto_tsquery)
    - Both can be combined: tag filter narrows, keyword ranks
    """
    conditions = [f"agent_name = %s"]
    params: list = [agent_name]

    # Tier filter + time window
    if tier == "short":
        conditions.append("tier = 'short'")
        conditions.append("created_at > NOW() - INTERVAL '30 days'")
    elif tier == "long":
        conditions.append("tier = 'long'")
        # No time limit for long-term
    else:  # "all"
        # Short: last 30 days. Long: all time.
        conditions.append(
            "(tier = 'long' OR (tier = 'short' AND created_at > NOW() - INTERVAL '30 days'))"
        )

    if tags:
        conditions.append("tags && %s")
        params.append(tags)

    if query:
        conditions.append(
            "to_tsvector('english', content) @@ plainto_tsquery('english', %s)"
        )
        params.append(query)

    where = " AND ".join(conditions)

    # Long-term first (more valuable), then short-term by recency
    async with get_connection() as conn:
        rows = await conn.execute(
            f"""SELECT content, tags, tier, created_at
                FROM {SCHEMA}.memories
                WHERE {where}
                ORDER BY
                    CASE tier WHEN 'long' THEN 0 ELSE 1 END,
                    created_at DESC
                LIMIT 20""",
            params,
        ).fetchall()

    # Enforce token cap
    results = []
    total_chars = 0
    for row in rows:
        entry_len = len(row["content"]) + len(",".join(row["tags"])) + 15
        if total_chars + entry_len > MAX_MEMORY_CHARS:
            break
        results.append(dict(row))
        total_chars += entry_len

    return results

async def prune_memories(retention_days: int = 90):
    """Delete memories older than retention period."""
    async with get_connection() as conn:
        await conn.execute(
            f"DELETE FROM {SCHEMA}.memories WHERE created_at < NOW() - INTERVAL '%s days'",
            (retention_days,),
        )
```

**New migration** for memories table:

```sql
CREATE TABLE IF NOT EXISTS ${SCHEMA}.memories (
    id BIGSERIAL PRIMARY KEY,
    agent_name VARCHAR(64) NOT NULL,
    content TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    tier VARCHAR(8) NOT NULL DEFAULT 'short' CHECK (tier IN ('short', 'long')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_memories_agent
    ON ${SCHEMA}.memories (agent_name, tier);
CREATE INDEX idx_memories_tags
    ON ${SCHEMA}.memories USING GIN (tags);
CREATE INDEX idx_memories_fts
    ON ${SCHEMA}.memories USING GIN (to_tsvector('english', content));
```

**Search examples:**

```sql
-- By tags: find all memories tagged 'boss' and 'preference'
SELECT * FROM memories WHERE agent_name = 'robin' AND tags && '{boss,preference}';

-- By keyword: full-text search for "PR size"
SELECT * FROM memories WHERE agent_name = 'robin'
  AND to_tsvector('english', content) @@ plainto_tsquery('english', 'PR size');

-- Combined: tag 'boss' + keyword 'PR'
SELECT * FROM memories WHERE agent_name = 'robin'
  AND tags && '{boss}'
  AND to_tsvector('english', content) @@ plainto_tsquery('english', 'PR');
```

No embedding model, no vector extension, no extra API calls. Pure Postgres.

**Future**: If semantic search is needed later, add an `embedding vector(1536)` column and a pgvector index. The search function can try tag/keyword first, fall back to similarity search.

### 4.7 Update agent loop

Integrate persistence into the loop:

```python
class AgentLoop:
    async def run(self, message: str, conversation_id: str, channel_type: str = "cli") -> str:
        # Load history from DB
        history = await load_history(conversation_id)

        # Truncate to fit context window
        history = build_context(
            system=self.system_prompt,
            history=history,
            tools=self.tool_registry.get_definitions(),
            model_config=self.model_config,
        )

        # Run LLM + tool loop
        response = await self._run_loop(message, history)

        # Save to DB
        await save_message(conversation_id, "user", message, channel_type=channel_type)
        await save_message(conversation_id, "assistant", response.content, channel_type=channel_type, tool_calls=response.tool_calls)

        return response.content
```

## Files to create/modify

| File | Action |
|------|--------|
| `src/inotagent/db/__init__.py` | Create |
| `src/inotagent/db/pool.py` | Create — async connection pool |
| `src/inotagent/db/conversations.py` | Create — conversation CRUD |
| `src/inotagent/db/memory.py` | Create — vector memory (can defer) |
| `src/inotagent/llm/tokens.py` | Modify — add context window management |
| `src/inotagent/loop.py` | Modify — integrate DB persistence |
| `infra/postgres/migrations/` | New migration for conversations + memories tables |
| `tests/test_conversations.py` | Create — persistence tests |

## Existing code to reuse

- `core/runtime/db.py` — connection pattern (adapt to async)
- `core/runtime/config.py` — `get_platform_schema()` for schema name
- pgvector already installed in Postgres image (`pgvector/pgvector:pg16`)

## How to verify

1. Chat with agent → restart container → chat again → agent remembers previous context
2. Long conversation (100+ messages) → context doesn't exceed model limit, oldest messages dropped
3. Check DB: `SELECT * FROM openvaia.conversations WHERE conversation_id = '...'`
4. Conversation pruning: old conversations deleted after retention period
5. (If memory implemented) Store a fact → search for it semantically → retrieve it
