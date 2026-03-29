"""Heartbeat — lightweight periodic pulse that detects new work and reports health.

Runs every 60s (configurable). No LLM calls — just DB queries and status updates.
Triggers the agent loop only when new tasks are detected and agent is idle.

Also runs a fast 1s web-message checker for UI chat responsiveness.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import UTC, date, datetime

from inotagent.db.pool import get_connection, get_schema

logger = logging.getLogger(__name__)

# Default heartbeat interval
DEFAULT_INTERVAL = 60

# Web message check interval (fast loop for UI chat)
WEB_CHECK_INTERVAL = 1


class Heartbeat:
    """Always-on heartbeat: health reporting, task detection, mission pickup, delegated review, web chat."""

    def __init__(self, agent_name: str, agent_loop, mission_tags: list[str] | None = None) -> None:
        self.agent_name = agent_name
        self.agent_loop = agent_loop
        self.mission_tags = mission_tags or []
        self._started_at = datetime.now(UTC)
        self._task: asyncio.Task | None = None
        self._web_task: asyncio.Task | None = None
        self._last_prune_date: date | None = None

    async def start(self) -> None:
        """Start the heartbeat and web-message background tasks."""
        self._task = asyncio.create_task(self._loop())
        self._web_task = asyncio.create_task(self._web_message_loop())
        logger.info(f"Heartbeat started for {self.agent_name}")

    async def stop(self) -> None:
        """Stop the heartbeat and web-message checker."""
        for t in (self._task, self._web_task):
            if t:
                t.cancel()
                try:
                    await t
                except asyncio.CancelledError:
                    pass
        self._task = None
        self._web_task = None
        logger.info(f"Heartbeat stopped for {self.agent_name}")

    async def _loop(self) -> None:
        interval = await _get_config_int("heartbeat.interval_seconds", DEFAULT_INTERVAL)
        while True:
            try:
                await self._beat()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Heartbeat error: {e}", exc_info=True)
            await asyncio.sleep(interval)

    async def _beat(self) -> None:
        """One heartbeat cycle."""
        # 0a. Check for restart request
        if await self._check_restart_requested():
            logger.info(f"Restart requested for {self.agent_name} — exiting for container restart")
            sys.exit(0)

        # 0b. Refresh skills cache
        try:
            await self.agent_loop.config.refresh_skills()
        except Exception as e:
            logger.warning(f"Skill refresh failed: {e}")

        # 1. Report health
        await self._report_health()

        # 2. Check for pending tasks (todo + stale in_progress)
        pending = await self._check_pending_tasks()
        if pending:
            logger.info(f"Heartbeat: {len(pending)} pending task(s) detected")
            await self._trigger_task_pickup(pending)
        elif not self.agent_loop.is_busy():
            stale = await self._check_stale_tasks()
            if stale:
                logger.info(f"Heartbeat: {len(stale)} stale in_progress task(s) detected")
                await self._trigger_stale_retry(stale)
        if not pending and self.mission_tags and not self.agent_loop.is_busy():
            # 2b. No assigned tasks — check mission board for unassigned backlog
            missions = await self._check_missions()
            if missions:
                logger.info(f"Heartbeat: {len(missions)} matching mission(s) on board")
                await self._trigger_mission_pickup(missions)

        # 3. Check for delegated tasks in review (created by me, completed by others)
        if not self.agent_loop.is_busy():
            reviews = await self._check_delegated_reviews()
            if reviews:
                logger.info(f"Heartbeat: {len(reviews)} delegated task(s) ready for review")
                await self._trigger_delegated_review(reviews)

        # 4. Reset recurring tasks that are due
        await self._reset_recurring_tasks()

        # 5. Daily data pruning
        today = date.today()
        if self._last_prune_date != today:
            await self._prune_old_data()
            self._last_prune_date = today

    async def _report_health(self) -> None:
        """Update agent status in DB."""
        schema = get_schema()
        uptime = (datetime.now(UTC) - self._started_at).total_seconds()
        details = json.dumps({
            "runtime": "inotagent",
            "uptime_seconds": int(uptime),
            "is_busy": self.agent_loop.is_busy(),
        })

        async with get_connection() as conn:
            await conn.execute(
                f"""INSERT INTO {schema}.agent_status
                    (agent_name, healthy, details, checked_at)
                    VALUES (%s, TRUE, %s, NOW())""",
                (self.agent_name, details),
            )
            await conn.execute(
                f"UPDATE {schema}.agents SET status = 'online', last_seen = NOW() WHERE name = %s",
                (self.agent_name,),
            )

    async def _check_pending_tasks(self) -> list[dict]:
        """Check for todo tasks assigned to this agent."""
        schema = get_schema()
        async with get_connection() as conn:
            cur = await conn.execute(
                f"""SELECT key, title, priority, created_by
                    FROM {schema}.tasks
                    WHERE assigned_to = %s AND status = 'todo'
                    ORDER BY
                        CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                                      WHEN 'medium' THEN 2 ELSE 3 END,
                        created_at ASC
                    LIMIT 5""",
                (self.agent_name,),
            )
            rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def _check_stale_tasks(self) -> list[dict]:
        """Check for in_progress tasks with no update in 30+ minutes (likely failed)."""
        schema = get_schema()
        async with get_connection() as conn:
            cur = await conn.execute(
                f"""SELECT key, title, priority, created_by
                    FROM {schema}.tasks
                    WHERE assigned_to = %s AND status = 'in_progress'
                      AND updated_at < NOW() - INTERVAL '30 minutes'
                    ORDER BY
                        CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                                      WHEN 'medium' THEN 2 ELSE 3 END,
                        updated_at ASC
                    LIMIT 3""",
                (self.agent_name,),
            )
            rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def _trigger_stale_retry(self, tasks: list[dict]) -> None:
        """Retry a stale in_progress task — conversation history is preserved."""
        if self.agent_loop.is_busy():
            logger.debug("Heartbeat: agent busy, skipping stale retry")
            return

        top = tasks[0]
        prompt = (
            f"You have a stale task that appears to have failed: {top['key']} [{top['priority']}] \"{top['title']}\". "
            f"It has been in_progress for over 30 minutes with no update. "
            f"Review what you attempted previously (your conversation history is preserved) "
            f"and try a different approach. Follow your AGENTS.md workflow."
        )
        conversation_id = f"heartbeat-task-{self.agent_name}-{top['key']}"
        asyncio.create_task(
            self.agent_loop.run(prompt, conversation_id=conversation_id, channel_type="cron")
        )

    async def _trigger_task_pickup(self, tasks: list[dict]) -> None:
        """If agent is idle, trigger task pickup via agent loop."""
        if self.agent_loop.is_busy():
            logger.debug("Heartbeat: agent busy, skipping task pickup")
            return

        top = tasks[0]
        prompt = (
            f"You have a pending task: {top['key']} [{top['priority']}] \"{top['title']}\" "
            f"(assigned by {top['created_by']}). "
            f"Set it to in_progress and start working on it. "
            f"Follow your AGENTS.md workflow — announce on Discord when starting."
        )
        conversation_id = f"heartbeat-task-{self.agent_name}-{top['key']}"
        asyncio.create_task(
            self.agent_loop.run(prompt, conversation_id=conversation_id, channel_type="cron")
        )

    async def _check_missions(self) -> list[dict]:
        """Check for unassigned backlog tasks matching this agent's mission_tags."""
        schema = get_schema()
        async with get_connection() as conn:
            cur = await conn.execute(
                f"""SELECT key, title, priority, tags, created_by
                    FROM {schema}.tasks
                    WHERE status = 'backlog'
                      AND assigned_to IS NULL
                      AND tags && %s
                    ORDER BY
                        CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                                      WHEN 'medium' THEN 2 ELSE 3 END,
                        created_at ASC
                    LIMIT 3""",
                (self.mission_tags,),
            )
            rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def _trigger_mission_pickup(self, missions: list[dict]) -> None:
        """If agent is idle, trigger mission pickup via agent loop."""
        if self.agent_loop.is_busy():
            logger.debug("Heartbeat: agent busy, skipping mission pickup")
            return

        top = missions[0]
        tags_str = ", ".join(top.get("tags", []))
        prompt = (
            f"You found an unassigned mission on the board: {top['key']} [{top['priority']}] "
            f"\"{top['title']}\" (tags: {tags_str}). "
            f"First assign it to yourself: task_update(key=\"{top['key']}\", assigned_to=\"{self.agent_name}\"). "
            f"Then set it to in_progress and start working on it. "
            f"Follow your AGENTS.md workflow."
        )
        conversation_id = f"heartbeat-mission-{self.agent_name}-{top['key']}"
        asyncio.create_task(
            self.agent_loop.run(prompt, conversation_id=conversation_id, channel_type="cron")
        )

    async def _check_delegated_reviews(self) -> list[dict]:
        """Check for tasks created by this agent that are now in review status."""
        schema = get_schema()
        async with get_connection() as conn:
            cur = await conn.execute(
                f"""SELECT key, title, priority, assigned_to, result
                    FROM {schema}.tasks
                    WHERE created_by = %s
                      AND assigned_to != %s
                      AND status = 'review'
                    ORDER BY updated_at ASC
                    LIMIT 5""",
                (self.agent_name, self.agent_name),
            )
            rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def _trigger_delegated_review(self, reviews: list[dict]) -> None:
        """If agent is idle, trigger review of delegated tasks."""
        if self.agent_loop.is_busy():
            logger.debug("Heartbeat: agent busy, skipping delegated review")
            return

        top = reviews[0]
        result_str = f" Result: \"{top['result']}\"" if top.get("result") else ""
        prompt = (
            f"A task you delegated is ready for review: {top['key']} [{top['priority']}] "
            f"\"{top['title']}\" (assigned to {top['assigned_to']}).{result_str} "
            f"Review the work. If satisfactory, set status to done. "
            f"If changes needed, set status back to todo with feedback. "
            f"Follow your AGENTS.md 'Verify Created Tasks' workflow."
        )
        conversation_id = f"heartbeat-review-{self.agent_name}-{top['key']}"
        asyncio.create_task(
            self.agent_loop.run(prompt, conversation_id=conversation_id, channel_type="cron")
        )

    # --- Web message fast loop (1s) ---

    async def _web_message_loop(self) -> None:
        """Fast 1s loop that checks for unprocessed web chat messages."""
        while True:
            try:
                await self._check_web_messages()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Web message check error: {e}", exc_info=True)
            await asyncio.sleep(WEB_CHECK_INTERVAL)

    async def _check_web_messages(self) -> None:
        """Look for unprocessed user messages from web chat and trigger agent loop."""
        schema = get_schema()
        async with get_connection() as conn:
            cur = await conn.execute(
                f"""SELECT id, conversation_id, content
                    FROM {schema}.conversations
                    WHERE agent_name = %s
                      AND channel_type = 'web'
                      AND role = 'user'
                      AND processed_at IS NULL
                    ORDER BY created_at ASC
                    LIMIT 1""",
                (self.agent_name,),
            )
            row = await cur.fetchone()

        if not row:
            return

        if self.agent_loop.is_busy():
            logger.debug("Web message waiting: agent busy")
            return

        # Mark as processed immediately to prevent double-pickup
        async with get_connection() as conn:
            await conn.execute(
                f"UPDATE {schema}.conversations SET processed_at = NOW() WHERE id = %s",
                (row["id"],),
            )

        conversation_id = row["conversation_id"]
        logger.info(f"Web chat: processing message in {conversation_id}")

        asyncio.create_task(
            self.agent_loop.run(
                row["content"],
                conversation_id=conversation_id,
                channel_type="web",
                skip_save_user=True,
            )
        )

    async def _check_restart_requested(self) -> bool:
        """Check if a restart has been requested via agent_configs."""
        schema = get_schema()
        try:
            async with get_connection() as conn:
                cur = await conn.execute(
                    f"""SELECT value FROM {schema}.agent_configs
                        WHERE agent_name = %s AND key = 'restart_requested'""",
                    (self.agent_name,),
                )
                row = await cur.fetchone()
                if row and row["value"].lower() in ("true", "1", "yes"):
                    # Clear the flag before exiting
                    await conn.execute(
                        f"""DELETE FROM {schema}.agent_configs
                            WHERE agent_name = %s AND key = 'restart_requested'""",
                        (self.agent_name,),
                    )
                    return True
        except Exception as e:
            logger.debug(f"Restart check failed: {e}")
        return False

    async def _reset_recurring_tasks(self) -> None:
        """Reset completed recurring tasks that are due for their next run.

        Two modes:
        - schedule_at (fixed time): resets at a specific UTC time daily (e.g., '00:00')
          Triggers when: current time >= schedule_at AND last_completed_at < today's schedule_at
        - interval (relative): resets after N minutes since last completion
          Triggers when: last_completed_at + interval < NOW()
        """
        schema = get_schema()
        try:
            async with get_connection() as conn:
                # Mode 1a: Fixed schedule_at time (daily/weekly — interval-based)
                cur = await conn.execute(
                    f"""UPDATE {schema}.tasks
                        SET status = 'todo', updated_at = NOW(), recurrence_count = recurrence_count + 1
                        WHERE assigned_to = %s
                          AND status IN ('done', 'review')
                          AND schedule_at IS NOT NULL
                          AND recurrence_minutes > 0
                          AND CURRENT_TIME >= schedule_at
                          AND (last_completed_at IS NULL
                               OR last_completed_at + (recurrence_minutes || ' minutes')::interval
                                  < date_trunc('day', NOW()) + schedule_at)
                        RETURNING key, title, recurrence_count""",
                    (self.agent_name,),
                )
                fixed_rows = await cur.fetchall()

                # Mode 1b: Fixed schedule_at time (monthly — calendar-accurate)
                # recurrence_minutes = -1 means calendar month
                # Triggers when current month/year differs from last completion month/year
                cur = await conn.execute(
                    f"""UPDATE {schema}.tasks
                        SET status = 'todo', updated_at = NOW(), recurrence_count = recurrence_count + 1
                        WHERE assigned_to = %s
                          AND status IN ('done', 'review')
                          AND schedule_at IS NOT NULL
                          AND recurrence_minutes = -1
                          AND CURRENT_TIME >= schedule_at
                          AND (last_completed_at IS NULL
                               OR (extract(year FROM NOW()) * 12 + extract(month FROM NOW()))
                                  > (extract(year FROM last_completed_at) * 12 + extract(month FROM last_completed_at)))
                        RETURNING key, title, recurrence_count""",
                    (self.agent_name,),
                )
                fixed_rows = fixed_rows + await cur.fetchall()

                # Mode 2: Interval-based (N minutes after last completion)
                cur = await conn.execute(
                    f"""UPDATE {schema}.tasks
                        SET status = 'todo', updated_at = NOW(), recurrence_count = recurrence_count + 1
                        WHERE assigned_to = %s
                          AND status IN ('done', 'review')
                          AND recurrence_minutes IS NOT NULL
                          AND schedule_at IS NULL
                          AND last_completed_at IS NOT NULL
                          AND last_completed_at + (recurrence_minutes || ' minutes')::interval < NOW()
                        RETURNING key, title, recurrence_count""",
                    (self.agent_name,),
                )
                interval_rows = await cur.fetchall()

                rows = fixed_rows + interval_rows
                if rows:
                    info = [f"{r['key']}(cycle {r['recurrence_count']})" for r in rows]
                    logger.info(f"Reset {len(rows)} recurring task(s): {info}")
        except Exception as e:
            logger.warning(f"Recurring task reset failed: {e}")

    async def _prune_old_data(self) -> None:
        """Daily cleanup of stale data."""
        schema = get_schema()
        async with get_connection() as conn:
            # Health records: keep 24 hours
            cur = await conn.execute(
                f"DELETE FROM {schema}.agent_status WHERE checked_at < NOW() - INTERVAL '24 hours'"
            )
            logger.info(f"Pruned {cur.rowcount} old health records")

            # Short-term memories: keep 30 days
            cur = await conn.execute(
                f"DELETE FROM {schema}.memories WHERE tier = 'short' AND created_at < NOW() - INTERVAL '30 days'"
            )
            if cur.rowcount:
                logger.info(f"Pruned {cur.rowcount} expired short-term memories")

            # Conversations: configurable retention (default 90 days)
            retention_days = await _get_config_int("conversations.retention_days", 90)
            cur = await conn.execute(
                f"DELETE FROM {schema}.conversations WHERE created_at < NOW() - INTERVAL '%s days'",
                (retention_days,),
            )
            if cur.rowcount:
                logger.info(f"Pruned {cur.rowcount} old conversation messages")


async def _get_config_int(key: str, default: int) -> int:
    """Read an integer config value from platform.config."""
    schema = get_schema()
    try:
        async with get_connection() as conn:
            cur = await conn.execute(
                f"SELECT value FROM {schema}.config WHERE key = %s",
                (key,),
            )
            row = await cur.fetchone()
        return int(row["value"]) if row else default
    except Exception:
        return default
