"""One-time bootstrap: register agent, ensure spaces, sync repos, announce."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
from pathlib import Path

import yaml

from inotagent.db.pool import get_connection, get_schema, init_pool

logger = logging.getLogger(__name__)


async def register_agent(agent_name: str, role: str = "") -> None:
    """Register or update agent in the agents table."""
    schema = get_schema()
    async with get_connection() as conn:
        await conn.execute(
            f"""INSERT INTO {schema}.agents (name, status, last_seen, role)
                VALUES (%s, 'starting', NOW(), %s)
                ON CONFLICT (name) DO UPDATE SET status = 'starting', last_seen = NOW(), role = %s""",
            (agent_name, role, role),
        )
    logger.info(f"Agent '{agent_name}' registered (role={role or 'none'})")


async def ensure_space(name: str, space_type: str) -> int:
    """Create a space if it doesn't exist, return its ID."""
    schema = get_schema()
    async with get_connection() as conn:
        cur = await conn.execute(
            f"""INSERT INTO {schema}.spaces (name, type)
                VALUES (%s, %s)
                ON CONFLICT (name) DO NOTHING
                RETURNING id""",
            (name, space_type),
        )
        row = await cur.fetchone()
        if row:
            logger.info(f"Created #{name} space (id={row['id']})")
            return row["id"]

        cur = await conn.execute(
            f"SELECT id FROM {schema}.spaces WHERE name = %s",
            (name,),
        )
        row = await cur.fetchone()
        return row["id"]


async def add_to_space(agent_name: str, space_name: str) -> None:
    """Ensure agent is a member of a space."""
    schema = get_schema()
    async with get_connection() as conn:
        cur = await conn.execute(
            f"SELECT id FROM {schema}.spaces WHERE name = %s",
            (space_name,),
        )
        space = await cur.fetchone()
        if not space:
            return

        await conn.execute(
            f"""INSERT INTO {schema}.space_members (space_id, agent_name)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING""",
            (space["id"], agent_name),
        )


async def add_all_agents_to_space(space_name: str) -> None:
    """Ensure all registered agents are members of a space."""
    schema = get_schema()
    async with get_connection() as conn:
        cur = await conn.execute(
            f"SELECT id FROM {schema}.spaces WHERE name = %s",
            (space_name,),
        )
        space = await cur.fetchone()
        if not space:
            return

        cur = await conn.execute(f"SELECT name FROM {schema}.agents")
        agents = await cur.fetchall()
        for agent in agents:
            await conn.execute(
                f"""INSERT INTO {schema}.space_members (space_id, agent_name)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING""",
                (space["id"], agent["name"]),
            )


async def send_announcement(agent_name: str, space_name: str, body: str) -> None:
    """Send a message to a space."""
    schema = get_schema()
    async with get_connection() as conn:
        cur = await conn.execute(
            f"SELECT id FROM {schema}.spaces WHERE name = %s",
            (space_name,),
        )
        space = await cur.fetchone()
        if not space:
            return

        await conn.execute(
            f"INSERT INTO {schema}.messages (from_agent, space_id, body) VALUES (%s, %s, %s)",
            (agent_name, space["id"], body),
        )


async def announce_pending_tasks(agent_name: str) -> None:
    """Check for pending tasks and announce them."""
    schema = get_schema()
    async with get_connection() as conn:
        cur = await conn.execute(
            f"""SELECT key, title, status, priority, created_by
                FROM {schema}.tasks
                WHERE assigned_to = %s AND status IN ('todo', 'in_progress')
                ORDER BY
                    CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                         WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END,
                    created_at DESC""",
            (agent_name,),
        )
        tasks = await cur.fetchall()

    if not tasks:
        logger.info(f"No pending tasks for '{agent_name}'")
        return

    lines = [f"{agent_name} has {len(tasks)} pending task(s):"]
    for t in tasks:
        icon = "🔄" if t["status"] == "in_progress" else "📌"
        lines.append(f"  {icon} {t['key']} [{t['priority']}] {t['title']} (from {t['created_by']})")

    summary = "\n".join(lines)
    logger.info(summary)
    await send_announcement("system", "tasks", summary)


async def seed_default_cron_jobs(agent_name: str) -> None:
    """Seed the default task_check cron job if not already present."""
    from inotagent.scheduler.cron import DEFAULT_TASK_CHECK_MINUTES, TASK_CHECK_PROMPT

    schema = get_schema()
    async with get_connection() as conn:
        await conn.execute(
            f"""INSERT INTO {schema}.cron_jobs (agent_name, name, prompt, interval_minutes)
                VALUES (%s, 'task_check', %s, %s)
                ON CONFLICT (COALESCE(agent_name, ''), name) DO NOTHING""",
            (agent_name, TASK_CHECK_PROMPT, DEFAULT_TASK_CHECK_MINUTES),
        )
    logger.info(f"Default cron jobs seeded for '{agent_name}'")


async def sync_repos(agent_name: str) -> None:
    """Clone or pull repos assigned to this agent."""
    schema = get_schema()
    workspace = os.environ.get("WORKSPACE_DIR", "/workspace")
    repos_dir = os.path.join(workspace, "repos")
    os.makedirs(repos_dir, exist_ok=True)

    async with get_connection() as conn:
        cur = await conn.execute(
            f"SELECT repo_name, repo_url FROM {schema}.agent_repos WHERE agent_name = %s",
            (agent_name,),
        )
        repos = await cur.fetchall()

    if not repos:
        logger.info(f"No repos assigned to '{agent_name}'")
        return

    for repo in repos:
        name = repo["repo_name"]
        url = repo["repo_url"]
        dest = os.path.join(repos_dir, name)

        if os.path.isdir(dest):
            logger.info(f"Pulling latest: {name}")
            subprocess.run(["git", "-C", dest, "fetch", "--all"], check=False)
            subprocess.run(["git", "-C", dest, "pull", "--ff-only"], check=False)
        else:
            logger.info(f"Cloning {url} -> {dest}")
            subprocess.run(["git", "clone", url, dest], check=True)


async def bootstrap(agent_name: str) -> None:
    """Full bootstrap sequence."""
    logger.info(f"Bootstrapping agent '{agent_name}'")

    # Read agent.yml
    agent_dir = os.environ.get("AGENT_DIR", f"/app/agents/{agent_name}")
    agent_yml = Path(agent_dir) / "agent.yml"
    data: dict = {}
    if agent_yml.exists():
        with open(agent_yml) as f:
            data = yaml.safe_load(f) or {}
    role = data.get("role", "")

    # Register agent
    await register_agent(agent_name, role=role)

    # Seed agent configs from agent.yml (preserves existing UI overrides)
    from inotagent.db.agent_configs import seed_agent_configs
    await seed_agent_configs(agent_name, data)

    # Ensure spaces exist
    await ensure_space("tasks", "room")
    await ensure_space("public", "public")

    # Add agent + all existing agents to spaces
    await add_to_space(agent_name, "tasks")
    await add_to_space(agent_name, "public")
    await add_all_agents_to_space("tasks")

    # Announce boot
    await send_announcement(agent_name, "public", f"{agent_name} is online (inotagent)")

    # Announce pending tasks
    await announce_pending_tasks(agent_name)

    # Seed default cron jobs
    # Cron jobs removed — recurring tasks via heartbeat replace them
    # await seed_default_cron_jobs(agent_name)

    # Sync repos
    await sync_repos(agent_name)

    logger.info(f"Bootstrap complete for '{agent_name}'")


def main() -> None:
    """CLI entry point for bootstrap."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    agent_name = os.environ.get("AGENT_NAME")
    if not agent_name:
        raise RuntimeError("AGENT_NAME environment variable required")

    async def run():
        await init_pool()
        try:
            await bootstrap(agent_name)
        finally:
            from inotagent.db.pool import close_pool
            await close_pool()

    asyncio.run(run())


if __name__ == "__main__":
    main()
