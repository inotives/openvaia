"""Memory tools — store and search agent memories via Postgres.

Two tiers:
- short: Recent context, auto-pruned after 30 days
- long: Durable knowledge, never auto-pruned
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

MEMORY_STORE_TOOL = {
    "name": "memory_store",
    "description": (
        "Store information for future reference. "
        "Use 'short' for temporary context, 'long' for durable knowledge."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "The memory to store"},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags for categorization (e.g. 'script', 'preference', 'decision')",
            },
            "tier": {
                "type": "string",
                "enum": ["short", "long"],
                "description": "short = recent context (auto-pruned 30 days). long = durable knowledge.",
            },
        },
        "required": ["content", "tags", "tier"],
    },
}

MEMORY_SEARCH_TOOL = {
    "name": "memory_search",
    "description": (
        "Search your memories. Long-term is always searched (no time limit), "
        "short-term limited to last 30 days."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Keyword search query"},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Filter by tags",
            },
            "tier": {
                "type": "string",
                "enum": ["short", "long", "all"],
                "description": "Which tier to search (default: all)",
            },
        },
    },
}

MEMORY_TOOLS = [MEMORY_STORE_TOOL, MEMORY_SEARCH_TOOL]

_DB_NOT_CONNECTED = "Error: Database not connected. Memory tools require a running Postgres instance."


class MemoryTools:
    """Memory tool handlers backed by async Postgres."""

    def __init__(self, agent_name: str, db_available: bool = False) -> None:
        self.agent_name = agent_name
        self.db_available = db_available

    async def memory_store(
        self,
        content: str,
        tags: list[str],
        tier: str = "short",
    ) -> str:
        if not self.db_available:
            return _DB_NOT_CONNECTED

        from inotagent.db.memory import store_memory
        await store_memory(self.agent_name, content, tags, tier)
        return f"Stored in {tier}-term memory with tags: {', '.join(tags)}"

    async def memory_search(
        self,
        query: str | None = None,
        tags: list[str] | None = None,
        tier: str = "all",
    ) -> str:
        if not self.db_available:
            return _DB_NOT_CONNECTED

        from inotagent.db.memory import search_memory
        results = await search_memory(self.agent_name, query=query, tags=tags, tier=tier)

        if not results:
            return "No memories found."

        lines = []
        for r in results:
            tag_str = ",".join(r["tags"]) if r["tags"] else "none"
            lines.append(f"[{r['tier']}:{tag_str}] {r['content']}")
        return "\n---\n".join(lines)
