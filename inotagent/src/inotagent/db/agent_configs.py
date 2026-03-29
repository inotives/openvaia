"""DB helpers for agent_configs table."""

from __future__ import annotations

import json
import logging

from inotagent.db.pool import get_connection, get_schema

logger = logging.getLogger(__name__)


async def load_agent_configs(agent_name: str) -> dict[str, str]:
    """Load all config key-value pairs for an agent from the DB.

    Returns a dict mapping key -> value (both strings).
    """
    schema = get_schema()
    async with get_connection() as conn:
        cur = await conn.execute(
            f"SELECT key, value FROM {schema}.agent_configs WHERE agent_name = %s",
            (agent_name,),
        )
        rows = await cur.fetchall()
    return {row["key"]: row["value"] for row in rows}


async def seed_agent_configs(agent_name: str, agent_data: dict) -> None:
    """Seed agent_configs from agent.yml data.

    Only inserts keys that don't already exist (preserves UI overrides).
    """
    schema = get_schema()

    config_items = [
        ("model", agent_data.get("model", ""), "Primary LLM model"),
        ("fallbacks", json.dumps(agent_data.get("fallbacks", [])), "Fallback models (JSON array)"),
        ("mission_tags", json.dumps(agent_data.get("mission_tags", [])), "Mission board tags (JSON array)"),
        ("parallel", str(agent_data.get("parallel", False)).lower(), "Enable parallel tool execution"),
    ]

    async with get_connection() as conn:
        for key, value, description in config_items:
            await conn.execute(
                f"""INSERT INTO {schema}.agent_configs (agent_name, key, value, source, description)
                    VALUES (%s, %s, %s, 'yaml', %s)
                    ON CONFLICT (agent_name, key) DO NOTHING""",
                (agent_name, key, value, description),
            )

    logger.info(f"Agent configs seeded for '{agent_name}'")


async def upsert_agent_config(agent_name: str, key: str, value: str, description: str = "") -> None:
    """Upsert a single agent config key-value pair."""
    schema = get_schema()
    async with get_connection() as conn:
        await conn.execute(
            f"""INSERT INTO {schema}.agent_configs (agent_name, key, value, source, description)
                VALUES (%s, %s, %s, 'system', %s)
                ON CONFLICT (agent_name, key) DO UPDATE SET value = EXCLUDED.value""",
            (agent_name, key, value, description),
        )
