"""Research report storage — persistent, searchable research reports."""

from __future__ import annotations

import logging

from inotagent.db.pool import get_connection, get_schema

logger = logging.getLogger(__name__)

MAX_SEARCH_CHARS = 12000


async def store_report(
    agent_name: str,
    title: str,
    summary: str,
    body: str,
    tags: list[str] | None = None,
    task_key: str | None = None,
) -> int:
    """Store a research report. Returns the report ID."""
    schema = get_schema()
    async with get_connection() as conn:
        cur = await conn.execute(
            f"""INSERT INTO {schema}.research_reports
                (agent_name, task_key, title, summary, body, tags)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id""",
            (agent_name, task_key, title, summary, body, tags or []),
        )
        row = await cur.fetchone()
    return row["id"]


async def search_reports(
    agent_name: str | None = None,
    query: str | None = None,
    tags: list[str] | None = None,
) -> list[dict]:
    """Search research reports by keywords and/or tags.

    Returns summaries by default (not full body) to save tokens.
    """
    schema = get_schema()
    conditions: list[str] = []
    params: list = []

    if agent_name:
        conditions.append("agent_name = %s")
        params.append(agent_name)

    if tags:
        conditions.append("tags && %s")
        params.append(tags)

    if query:
        conditions.append(
            "to_tsvector('english', title || ' ' || summary || ' ' || body) "
            "@@ plainto_tsquery('english', %s)"
        )
        params.append(query)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    async with get_connection() as conn:
        cur = await conn.execute(
            f"""SELECT id, agent_name, task_key, title, summary, tags, created_at
                FROM {schema}.research_reports
                {where}
                ORDER BY created_at DESC
                LIMIT 20""",
            params,
        )
        rows = await cur.fetchall()

    results: list[dict] = []
    total_chars = 0
    for row in rows:
        entry_len = len(row["title"]) + len(row["summary"]) + 30
        if total_chars + entry_len > MAX_SEARCH_CHARS:
            break
        results.append(dict(row))
        total_chars += entry_len

    return results


async def get_report(report_id: int) -> dict | None:
    """Get a full research report by ID (includes body)."""
    schema = get_schema()
    async with get_connection() as conn:
        cur = await conn.execute(
            f"""SELECT id, agent_name, task_key, title, summary, body, tags, created_at
                FROM {schema}.research_reports
                WHERE id = %s""",
            (report_id,),
        )
        row = await cur.fetchone()
    return dict(row) if row else None
