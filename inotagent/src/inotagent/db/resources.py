"""Curated resources registry — priority-scored trusted sources for research."""

from __future__ import annotations

import logging

from inotagent.db.pool import get_connection, get_schema

logger = logging.getLogger(__name__)


async def search_resources(
    tags: list[str] | None = None,
    query: str | None = None,
) -> list[dict]:
    """Search active resources by tags and/or keyword. Ordered by priority descending."""
    schema = get_schema()
    conditions = ["status = 'active'"]
    params: list = []

    if tags:
        conditions.append("tags && %s")
        params.append(tags)

    if query:
        conditions.append(
            "(name ILIKE %s OR description ILIKE %s OR notes ILIKE %s)"
        )
        like = f"%{query}%"
        params.extend([like, like, like])

    where = " AND ".join(conditions)

    async with get_connection() as conn:
        cur = await conn.execute(
            f"""SELECT id, url, name, description, tags, notes, priority, status, created_by, created_at
                FROM {schema}.resources
                WHERE {where}
                ORDER BY priority DESC, name
                LIMIT 20""",
            params,
        )
        rows = await cur.fetchall()

    return [dict(r) for r in rows]


async def add_resource(
    url: str,
    name: str,
    description: str,
    tags: list[str],
    notes: str | None = None,
    created_by: str | None = None,
) -> None:
    """Add a new resource as draft (requires human approval)."""
    schema = get_schema()
    async with get_connection() as conn:
        await conn.execute(
            f"""INSERT INTO {schema}.resources (url, name, description, tags, notes, status, created_by)
                VALUES (%s, %s, %s, %s, %s, 'draft', %s)""",
            (url, name, description, tags, notes or "", created_by),
        )
