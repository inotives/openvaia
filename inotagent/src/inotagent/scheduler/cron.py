"""Cron scheduler — periodic full agent sessions on a timer.

Unlike heartbeat (cheap DB checks), cron triggers expensive LLM calls.
Jobs are loaded from the cron_jobs table at startup. Supports global jobs
(agent_name IS NULL) with per-agent overrides.

Scheduling is UTC-aligned: jobs run at fixed intervals from midnight UTC.
E.g., 12h interval → 00:00, 12:00 UTC; 4h → 00:00, 04:00, 08:00, ... UTC.
"""

from __future__ import annotations

import asyncio
import logging
import math
from datetime import UTC, date, datetime, timedelta

from inotagent.db.pool import get_connection, get_schema

logger = logging.getLogger(__name__)

DEFAULT_DAILY_REVIEW_MINUTES = 1440  # 24h, UTC-aligned to 00:00

# Task check prompt — role-neutral, skills define how to work
TASK_CHECK_PROMPT = (
    "Check your task queue for pending work. "
    "List your assigned tasks with status todo or in_progress. "
    "If you have todo tasks, pick the highest priority one, set it to in_progress, and start working on it. "
    "If you have in_progress tasks, continue working on them. "
    "If no tasks, do nothing — do NOT post to Discord or announce that you are idle. "
    "Follow your task_workflow skill for how to execute the task. "
    "When you start or complete a task, report progress via your configured channels."
)

# Default cron interval in minutes
DEFAULT_TASK_CHECK_MINUTES = 30


class Scheduler:
    """Cron-style scheduler for periodic agent sessions.

    Loads jobs from the cron_jobs table. Supports:
    - Per-agent jobs (agent_name = <name>)
    - Global jobs (agent_name IS NULL) — run by all agents
    - Per-agent overrides of global jobs (same name, specific agent_name)
    """

    def __init__(self, agent_name: str, agent_loop) -> None:
        self.agent_name = agent_name
        self.agent_loop = agent_loop
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        """Load jobs from DB and start recurring tasks."""
        jobs = await self._load_cron_jobs()

        if not jobs:
            logger.info(f"No cron jobs found for {self.agent_name}")
            return

        for job in jobs:
            self._tasks.append(
                asyncio.create_task(
                    self._run_recurring(
                        job_id=job["id"],
                        name=job["name"],
                        interval_seconds=job["interval_minutes"] * 60,
                        prompt=job["prompt"],
                        last_run_at=job.get("last_run_at"),
                    )
                )
            )
            logger.info(
                f"Cron [{job['name']}] started for {self.agent_name} "
                f"(every {job['interval_minutes']}min, id={job['id']})"
            )

    async def stop(self) -> None:
        """Cancel all running cron tasks."""
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()
        logger.info(f"Cron stopped for {self.agent_name}")

    async def _run_recurring(
        self, job_id: int, name: str, interval_seconds: int, prompt: str,
        last_run_at: datetime | None = None,
    ) -> None:
        """Run a prompt at UTC-aligned intervals.

        Jobs run at fixed intervals from midnight UTC:
        - 720min (12h) → 00:00, 12:00 UTC
        - 240min (4h)  → 00:00, 04:00, 08:00, 12:00, ... UTC
        - 30min        → 00:00, 00:30, 01:00, ... UTC
        """
        interval_minutes = interval_seconds // 60
        wait = _seconds_until_next_slot(interval_minutes, last_run_at)
        next_run = datetime.now(UTC) + timedelta(seconds=wait)
        logger.info(
            f"Cron [{name}] next run at {next_run.strftime('%H:%M')} UTC "
            f"(in {wait:.0f}s, every {interval_minutes}min)"
        )
        await asyncio.sleep(wait)

        while True:
            try:
                # Skip expensive LLM call if no pending work (task_check only)
                if name == "task_check" and not await self._has_pending_work():
                    logger.debug(f"Cron [{name}] skipped for {self.agent_name} — no pending work")
                else:
                    conversation_id = f"cron-{name}-{self.agent_name}-{date.today()}"
                    logger.info(f"Cron [{name}] firing for {self.agent_name}")
                    await self.agent_loop.run(
                        prompt,
                        conversation_id=conversation_id,
                        channel_type="cron",
                    )
                    logger.info(f"Cron [{name}] completed for {self.agent_name}")

                # Update last_run_at
                await self._update_last_run(job_id)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Cron [{name}] failed: {e}", exc_info=True)

            # Wait until next UTC-aligned slot
            wait = _seconds_until_next_slot(interval_minutes)
            await asyncio.sleep(wait)

    async def _has_pending_work(self) -> bool:
        """Quick DB check — are there todo/in_progress tasks for this agent?"""
        schema = get_schema()
        try:
            async with get_connection() as conn:
                cur = await conn.execute(
                    f"""SELECT COUNT(*) AS cnt FROM {schema}.tasks
                        WHERE assigned_to = %s AND status IN ('todo', 'in_progress')""",
                    (self.agent_name,),
                )
                row = await cur.fetchone()
            return row["cnt"] > 0
        except Exception:
            # On DB error, let the LLM call proceed as fallback
            return True

    async def _update_last_run(self, job_id: int) -> None:
        """Update last_run_at for a cron job."""
        schema = get_schema()
        try:
            async with get_connection() as conn:
                await conn.execute(
                    f"UPDATE {schema}.cron_jobs SET last_run_at = NOW() WHERE id = %s",
                    (job_id,),
                )
        except Exception as e:
            logger.warning(f"Failed to update last_run_at for job {job_id}: {e}")

    async def _load_cron_jobs(self) -> list[dict]:
        """Load enabled cron jobs for this agent from DB.

        Uses DISTINCT ON (name) to deduplicate: if an agent-specific override
        exists for a global job, the override wins (ORDER BY agent_name NULLS LAST).
        """
        schema = get_schema()
        try:
            async with get_connection() as conn:
                cur = await conn.execute(
                    f"""SELECT DISTINCT ON (name) id, name, prompt, interval_minutes, last_run_at
                        FROM {schema}.cron_jobs
                        WHERE enabled = true
                          AND (agent_name = %s OR agent_name IS NULL)
                        ORDER BY name, agent_name NULLS LAST""",
                    (self.agent_name,),
                )
                rows = await cur.fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"Failed to load cron jobs: {e}")
            return []


def _seconds_until_next_slot(
    interval_minutes: int,
    last_run_at: datetime | None = None,
) -> float:
    """Calculate seconds until the next UTC-aligned slot.

    Slots are fixed intervals from midnight UTC:
    - 720min → 00:00, 12:00
    - 240min → 00:00, 04:00, 08:00, 12:00, 16:00, 20:00
    - 30min  → 00:00, 00:30, 01:00, ...

    If last_run_at is None or before the most recent slot, the next slot
    is returned (which may be very soon — i.e., run almost immediately
    if a slot was just missed).
    """
    now = datetime.now(UTC)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    minutes_since_midnight = (now - midnight).total_seconds() / 60

    # Current slot index (the slot that just passed or is exactly now)
    current_slot = math.floor(minutes_since_midnight / interval_minutes)
    next_slot_minutes = (current_slot + 1) * interval_minutes
    next_run = midnight + timedelta(minutes=next_slot_minutes)

    # If last_run_at covers the current slot, wait for next slot
    # If last_run_at is missing or old, check if current slot is still valid
    current_slot_time = midnight + timedelta(minutes=current_slot * interval_minutes)
    if last_run_at is None or last_run_at < current_slot_time:
        # Current slot hasn't been run — run at current slot time
        # If current slot time is in the past (it usually is), run immediately
        wait = max((current_slot_time - now).total_seconds(), 0)
    else:
        # Current slot already ran — wait for next
        wait = (next_run - now).total_seconds()

    # Minimum 1s wait to avoid tight loops
    return max(wait, 1.0)
