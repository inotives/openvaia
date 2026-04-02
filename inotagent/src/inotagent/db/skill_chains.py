"""Skill chain matching and loading for dynamic skill equipping."""

from __future__ import annotations

import json
import logging

from inotagent.db.pool import get_connection, get_schema

logger = logging.getLogger(__name__)


async def match_chain(tags: list[str], title: str = "") -> dict | None:
    """Match a task to a skill chain by tags first, then keywords.

    Priority:
    1. Exact tag match (most specific first — more tags matched = better)
    2. Keyword match on title
    3. None (no chain matched — fall back to static skills)
    """
    schema = get_schema()

    if not tags and not title:
        return None

    async with get_connection() as conn:
        # Try tag matching — find chains where ANY match_tag overlaps with task tags
        if tags:
            cur = await conn.execute(
                f"""SELECT id, name, description, match_tags, match_keywords, steps,
                    (SELECT COUNT(*) FROM unnest(match_tags) mt WHERE mt = ANY(%s::text[])) AS match_count
                    FROM {schema}.skill_chains
                    WHERE is_active = true AND match_tags && %s::text[]
                    ORDER BY match_count DESC
                    LIMIT 1""",
                (tags, tags),
            )
            row = await cur.fetchone()
            if row:
                chain = dict(row)
                chain["steps"] = json.loads(chain["steps"]) if isinstance(chain["steps"], str) else chain["steps"]
                logger.info(f"Chain matched by tags: {chain['name']} (tags: {tags})")
                return chain

        # Try keyword matching on title
        if title:
            title_lower = title.lower()
            cur = await conn.execute(
                f"""SELECT id, name, description, match_tags, match_keywords, steps
                    FROM {schema}.skill_chains
                    WHERE is_active = true AND match_keywords IS NOT NULL""",
            )
            rows = await cur.fetchall()
            for row in rows:
                chain = dict(row)
                keywords = chain.get("match_keywords") or []
                for kw in keywords:
                    if kw.lower() in title_lower:
                        chain["steps"] = json.loads(chain["steps"]) if isinstance(chain["steps"], str) else chain["steps"]
                        logger.info(f"Chain matched by keyword '{kw}': {chain['name']} (title: {title})")
                        return chain

    return None


async def get_chain_step_skills(chain: dict, step_index: int = 0) -> list[str]:
    """Get skill names for a specific step in a chain."""
    steps = chain.get("steps", [])
    if not steps or step_index >= len(steps):
        return []
    step = steps[step_index]
    return step.get("skills", [])


async def load_skills_by_names(skill_names: list[str]) -> list[dict]:
    """Load skills by their names. Returns list of {id, name, content}."""
    if not skill_names:
        return []

    schema = get_schema()
    async with get_connection() as conn:
        # Build parameterized query for IN clause
        placeholders = ", ".join(["%s"] * len(skill_names))
        cur = await conn.execute(
            f"""SELECT id, name, content
                FROM {schema}.skills
                WHERE name IN ({placeholders})
                  AND enabled = true
                  AND COALESCE(status, 'active') = 'active'""",
            skill_names,
        )
        rows = await cur.fetchall()
    return [dict(r) for r in rows]
