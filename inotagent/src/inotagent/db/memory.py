"""Memory storage — hybrid search (FTS + pgvector semantic) via Postgres."""

from __future__ import annotations

import logging

from inotagent.db.pool import get_connection, get_schema

logger = logging.getLogger(__name__)

# Max chars returned per search call (~2000 tokens)
MAX_MEMORY_CHARS = 8000


async def _get_embedding(text: str, input_type: str = "passage") -> list[float] | None:
    """Get embedding vector for text, or None if embedding client not available."""
    try:
        from inotagent.llm.embeddings import get_embedding_client
        client = get_embedding_client()
        if client is None:
            return None
        return await client.embed_one(text, input_type=input_type)
    except Exception as e:
        logger.warning(f"Embedding failed, falling back to FTS only: {e}")
        return None


async def store_memory(
    agent_name: str,
    content: str,
    tags: list[str],
    tier: str = "short",
) -> None:
    """Store a memory with tags, tier, and optional embedding vector."""
    schema = get_schema()
    embedding = await _get_embedding(content, input_type="passage")

    async with get_connection() as conn:
        if embedding is not None:
            await conn.execute(
                f"""INSERT INTO {schema}.memories (agent_name, content, tags, tier, embedding)
                    VALUES (%s, %s, %s, %s, %s::vector)""",
                (agent_name, content, tags, tier, str(embedding)),
            )
        else:
            await conn.execute(
                f"""INSERT INTO {schema}.memories (agent_name, content, tags, tier)
                    VALUES (%s, %s, %s, %s)""",
                (agent_name, content, tags, tier),
            )


async def search_memory(
    agent_name: str,
    query: str | None = None,
    tags: list[str] | None = None,
    tier: str = "all",
) -> list[dict]:
    """Search memories using hybrid ranking (FTS + vector similarity).

    When embeddings are available, results are ranked by a weighted blend:
    - FTS score (keyword match): 30% weight
    - Vector similarity (semantic match): 70% weight

    Falls back to FTS-only search when embeddings are unavailable.
    """
    schema = get_schema()

    # Try to get query embedding for semantic search
    query_embedding = None
    if query:
        query_embedding = await _get_embedding(query, input_type="query")

    # Build base WHERE conditions (agent + tier)
    base_conditions = ["m.agent_name = %s"]
    base_params: list = [agent_name]

    if tier == "short":
        base_conditions.append("m.tier = 'short'")
        base_conditions.append("m.created_at > NOW() - INTERVAL '30 days'")
    elif tier == "long":
        base_conditions.append("m.tier = 'long'")
    else:  # "all"
        base_conditions.append(
            "(m.tier = 'long' OR (m.tier = 'short' AND m.created_at > NOW() - INTERVAL '30 days'))"
        )

    if tags:
        base_conditions.append("m.tags && %s")
        base_params.append(tags)

    where = " AND ".join(base_conditions)

    # Hybrid search: FTS + vector similarity
    if query and query_embedding is not None:
        embedding_str = str(query_embedding)
        sql = f"""
            SELECT m.content, m.tags, m.tier, m.created_at,
                COALESCE(ts_rank(to_tsvector('english', m.content),
                         plainto_tsquery('english', %s)), 0) * 0.3
                + COALESCE(1 - (m.embedding <=> %s::vector), 0) * 0.7
                AS score
            FROM {schema}.memories m
            WHERE {where}
              AND (
                to_tsvector('english', m.content) @@ plainto_tsquery('english', %s)
                OR m.embedding IS NOT NULL
              )
            ORDER BY score DESC
            LIMIT 20
        """
        # Params: query (rank), embedding (distance), base_params..., query (FTS filter)
        params = [query, embedding_str] + base_params + [query]

    # FTS-only search (no embeddings available)
    elif query:
        sql = f"""
            SELECT m.content, m.tags, m.tier, m.created_at,
                ts_rank(to_tsvector('english', m.content),
                        plainto_tsquery('english', %s)) AS score
            FROM {schema}.memories m
            WHERE {where}
              AND to_tsvector('english', m.content) @@ plainto_tsquery('english', %s)
            ORDER BY score DESC
            LIMIT 20
        """
        # Params: query (rank), base_params..., query (FTS filter)
        params = [query] + base_params + [query]

    # No query — tag/tier filter only
    else:
        sql = f"""
            SELECT m.content, m.tags, m.tier, m.created_at, 0 AS score
            FROM {schema}.memories m
            WHERE {where}
            ORDER BY
                CASE m.tier WHEN 'long' THEN 0 ELSE 1 END,
                m.created_at DESC
            LIMIT 20
        """
        params = base_params

    async with get_connection() as conn:
        cur = await conn.execute(sql, params)
        rows = await cur.fetchall()

    # Enforce token cap
    results: list[dict] = []
    total_chars = 0
    for row in rows:
        entry_len = len(row["content"]) + len(",".join(row["tags"])) + 15
        if total_chars + entry_len > MAX_MEMORY_CHARS:
            break
        results.append(dict(row))
        total_chars += entry_len

    return results


async def prune_memories(retention_days: int = 30) -> int:
    """Delete short-term memories older than retention period. Returns count deleted."""
    schema = get_schema()
    async with get_connection() as conn:
        cur = await conn.execute(
            f"""DELETE FROM {schema}.memories
                WHERE tier = 'short' AND created_at < NOW() - INTERVAL '%s days'""",
            (retention_days,),
        )
        return cur.rowcount
