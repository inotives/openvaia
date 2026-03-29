"""Resource tools — search and propose curated research sources."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

RESOURCE_SEARCH_TOOL = {
    "name": "resource_search",
    "description": (
        "Search curated resources by tags or keywords. "
        "Use BEFORE general web search to find reliable, vetted sources first. "
        "Returns resources ordered by priority (highest first)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Topic tags to match (e.g. crypto, dex, solana, api)",
            },
            "query": {
                "type": "string",
                "description": "Optional keyword search in name/description/notes",
            },
        },
    },
}

RESOURCE_ADD_TOOL = {
    "name": "resource_add",
    "description": (
        "Propose a new curated resource. Created as draft — requires human approval. "
        "Use when you discover a reliable data source during research."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Resource URL"},
            "name": {"type": "string", "description": "Short name"},
            "description": {"type": "string", "description": "What this resource provides"},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Topic tags for categorization",
            },
            "notes": {
                "type": "string",
                "description": "Usage tips, rate limits, auth requirements",
            },
        },
        "required": ["url", "name", "description", "tags"],
    },
}

RESOURCE_TOOLS = [RESOURCE_SEARCH_TOOL, RESOURCE_ADD_TOOL]

_DB_NOT_CONNECTED = "Error: Database not connected. Resource tools require a running Postgres instance."


class ResourceTools:
    """Resource tool handlers backed by async Postgres."""

    def __init__(self, agent_name: str, db_available: bool = False) -> None:
        self.agent_name = agent_name
        self.db_available = db_available

    async def resource_search(
        self,
        tags: list[str] | None = None,
        query: str | None = None,
    ) -> str:
        if not self.db_available:
            return _DB_NOT_CONNECTED

        from inotagent.db.resources import search_resources
        results = await search_resources(tags=tags, query=query)

        if not results:
            return "No matching resources found."

        lines = []
        for r in results:
            tag_str = ", ".join(r["tags"]) if r["tags"] else ""
            notes = f" — {r['notes']}" if r.get("notes") else ""
            lines.append(f"[{r['priority']}] {r['name']}: {r['url']}\n  {r['description']}{notes}\n  Tags: {tag_str}")
        return "\n---\n".join(lines)

    async def resource_add(
        self,
        url: str,
        name: str,
        description: str,
        tags: list[str],
        notes: str = "",
    ) -> str:
        if not self.db_available:
            return _DB_NOT_CONNECTED

        from inotagent.db.resources import add_resource
        await add_resource(
            url=url, name=name, description=description,
            tags=tags, notes=notes, created_by=self.agent_name,
        )
        return f"Draft resource '{name}' proposed. It will be reviewed by a human before activation."
