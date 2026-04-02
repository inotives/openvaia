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

        # 5. Proactive idle behavior — if agent has no work, trigger autonomous action
        if not self.agent_loop.is_busy() and not pending:
            await self._check_idle_behavior()

        # 6. Daily data pruning
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
                f"""SELECT key, title, priority, created_by, tags
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
        """If agent is idle, trigger task pickup via agent loop with dynamic skill loading."""
        if self.agent_loop.is_busy():
            logger.debug("Heartbeat: agent busy, skipping task pickup")
            return

        top = tasks[0]
        task_tags = top.get("tags") or []

        # Dynamic skill loading — match task to chain and load phase skills
        try:
            from inotagent.db.skill_chains import match_chain, set_task_chain_state, clear_gate, load_skills_by_names
            import json as _json

            # Check if task already has a chain (resuming after gate approval)
            existing_state = await self._get_task_chain_state(top["key"])
            if existing_state and existing_state.get("gate_pending"):
                # Human approved — clear gate and load current phase skills
                await clear_gate(top["key"])
                phase_skills_names = existing_state.get("active_skills", [])
                logger.info(f"Gate cleared for {top['key']}, resuming phase: {existing_state.get('current_phase')}")
            elif not existing_state or not existing_state.get("chain_name"):
                # New task — match to chain
                chain = await match_chain(task_tags, top["title"])
                if chain:
                    await set_task_chain_state(top["key"], chain)

            skill_ids, skill_names, skill_content = await self.agent_loop.config.get_skills_for_task(
                task_tags=task_tags, task_title=top["title"]
            )
            # Snapshot static skills, override for this task, restore after
            _orig_ids = self.agent_loop.config._skill_ids
            _orig_names = self.agent_loop.config._skill_names
            _orig_content = self.agent_loop.config._skill_content
            self.agent_loop.config._skill_ids = skill_ids
            self.agent_loop.config._skill_names = skill_names
            self.agent_loop.config._skill_content = skill_content
        except Exception as e:
            logger.warning(f"Dynamic skill loading failed, using static: {e}")

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

        # Restore static skills — loop.py snapshots at conversation start
        try:
            self.agent_loop.config._skill_ids = _orig_ids
            self.agent_loop.config._skill_names = _orig_names
            self.agent_loop.config._skill_content = _orig_content
        except NameError:
            pass

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

    async def _get_task_chain_state(self, task_key: str) -> dict | None:
        """Get chain_state from a task."""
        schema = get_schema()
        try:
            async with get_connection() as conn:
                cur = await conn.execute(
                    f"SELECT chain_state FROM {schema}.tasks WHERE key = %s",
                    (task_key,),
                )
                row = await cur.fetchone()
            if not row or not row["chain_state"]:
                return None
            state = row["chain_state"]
            if isinstance(state, str):
                import json
                state = json.loads(state)
            return state
        except Exception:
            return None

    # --- Proactive idle behavior ---

    async def _check_idle_behavior(self) -> None:
        """If agent has been idle and proactive mode is enabled, trigger autonomous action."""
        # Check if proactive behavior is enabled
        enabled = await self._get_agent_config("proactive_enabled", "true")
        if enabled.lower() not in ("true", "1", "yes"):
            return

        # Check daily budget — limit autonomous LLM calls per day
        max_daily = int(await self._get_agent_config("proactive_max_daily", "6"))
        today_count = await self._get_today_autonomous_count()
        if today_count >= max_daily:
            logger.debug(f"Proactive: daily budget reached ({today_count}/{max_daily})")
            return

        # Check idle duration — only trigger after 15+ minutes of idleness
        idle_minutes = int(await self._get_agent_config("proactive_idle_minutes", "15"))
        if not await self._is_idle_for(idle_minutes):
            return

        logger.info(f"Proactive: agent idle for {idle_minutes}+ min, triggering idle behavior ({today_count + 1}/{max_daily})")

        prompt = (
            "You are currently idle — no pending tasks or messages. "
            "Follow the idle_behavior skill protocol. IMPORTANT: "
            "First check your recent tasks (task_list) to see what you did recently. "
            "Do NOT repeat the same type of work within 3 hours. "
            "Pick ONE action that is DIFFERENT from your recent work, "
            "create a task tagged autonomous:true assigned to yourself, "
            "and execute it. Keep it focused and under 10 minutes. "
            "If you have nothing new to do, skip this cycle entirely."
        )
        conversation_id = f"heartbeat-idle-{self.agent_name}-{datetime.now(UTC).strftime('%Y%m%d%H%M')}"
        asyncio.create_task(
            self.agent_loop.run(prompt, conversation_id=conversation_id, channel_type="cron")
        )

    async def _get_agent_config(self, key: str, default: str) -> str:
        """Read an agent-specific config value from agent_configs."""
        schema = get_schema()
        try:
            async with get_connection() as conn:
                cur = await conn.execute(
                    f"SELECT value FROM {schema}.agent_configs WHERE agent_name = %s AND key = %s",
                    (self.agent_name, key),
                )
                row = await cur.fetchone()
            return row["value"] if row else default
        except Exception:
            return default

    async def _get_today_autonomous_count(self) -> int:
        """Count autonomous conversations started today."""
        schema = get_schema()
        try:
            async with get_connection() as conn:
                cur = await conn.execute(
                    f"""SELECT COUNT(DISTINCT conversation_id) AS cnt
                        FROM {schema}.conversations
                        WHERE agent_name = %s
                          AND conversation_id LIKE 'heartbeat-idle-%%'
                          AND created_at >= date_trunc('day', NOW())""",
                    (self.agent_name,),
                )
                row = await cur.fetchone()
            return int(row["cnt"]) if row else 0
        except Exception:
            return 0

    async def _is_idle_for(self, minutes: int) -> bool:
        """Check if agent has been idle (no LLM activity) for N+ minutes."""
        schema = get_schema()
        try:
            async with get_connection() as conn:
                cur = await conn.execute(
                    f"""SELECT MAX(created_at) AS last_activity
                        FROM {schema}.conversations
                        WHERE agent_name = %s
                          AND role = 'assistant'""",
                    (self.agent_name,),
                )
                row = await cur.fetchone()
            if not row or not row["last_activity"]:
                return True  # No activity ever — definitely idle
            idle_since = (datetime.now(UTC) - row["last_activity"]).total_seconds()
            return idle_since >= minutes * 60
        except Exception:
            return False

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
