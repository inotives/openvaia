"""Load skills from the database for an agent."""

from __future__ import annotations

import logging

from inotagent.db.pool import get_connection, get_schema

logger = logging.getLogger(__name__)


async def load_agent_skills(agent_name: str) -> list[dict]:
    """Load resolved skills for an agent: global + equipped, with override logic.

    Returns skills sorted by priority. If an equipped skill has the same name
    as a global skill, the equipped version wins.
    """
    schema = get_schema()
    async with get_connection() as conn:
        cur = await conn.execute(
            f"""SELECT DISTINCT ON (s.name)
                    s.id, s.name, s.content,
                    COALESCE(ags.priority, 1000) AS priority,
                    CASE WHEN ags.agent_name IS NOT NULL THEN true ELSE false END AS equipped
                FROM {schema}.skills s
                LEFT JOIN {schema}.agent_skills ags
                  ON ags.skill_id = s.id AND ags.agent_name = %s
                WHERE s.enabled = true
                  AND COALESCE(s.status, 'active') = 'active'
                  AND (s.global = true OR ags.agent_name IS NOT NULL)
                ORDER BY s.name, equipped DESC, priority ASC""",
            (agent_name,),
        )
        rows = await cur.fetchall()
    return sorted([dict(r) for r in rows], key=lambda r: r["priority"])


async def load_skill_by_name(name: str) -> dict | None:
    """Load a single skill by name. Returns None if not found or not active."""
    schema = get_schema()
    async with get_connection() as conn:
        cur = await conn.execute(
            f"""SELECT id, name, content, tags
                FROM {schema}.skills
                WHERE name = %s AND enabled = true AND COALESCE(status, 'active') = 'active'""",
            (name,),
        )
        row = await cur.fetchone()
    return dict(row) if row else None
