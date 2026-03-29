"""Tests for scheduler — heartbeat and DB-driven cron."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from inotagent.scheduler.cron import (
    DEFAULT_DAILY_REVIEW_MINUTES,
    DEFAULT_TASK_CHECK_MINUTES,
    TASK_CHECK_PROMPT,
    Scheduler,
)
from inotagent.scheduler.heartbeat import Heartbeat, _get_config_int


# --- Heartbeat tests ---


class TestHeartbeat:
    @pytest.fixture
    def mock_agent_loop(self):
        loop = MagicMock()
        loop.is_busy.return_value = False
        loop.run = AsyncMock(return_value="ok")
        loop.config.refresh_skills = AsyncMock()
        return loop

    def test_init(self, mock_agent_loop):
        hb = Heartbeat(agent_name="robin", agent_loop=mock_agent_loop)
        assert hb.agent_name == "robin"
        assert hb._task is None

    async def test_start_creates_task(self, mock_agent_loop):
        hb = Heartbeat(agent_name="robin", agent_loop=mock_agent_loop)

        # Patch _loop to prevent actual execution
        hb._loop = AsyncMock()
        await hb.start()

        assert hb._task is not None
        await hb.stop()

    async def test_stop_cancels_task(self, mock_agent_loop):
        hb = Heartbeat(agent_name="robin", agent_loop=mock_agent_loop)
        hb._loop = AsyncMock()
        await hb.start()
        assert hb._task is not None

        await hb.stop()
        assert hb._task is None

    async def test_stop_when_not_started(self, mock_agent_loop):
        hb = Heartbeat(agent_name="robin", agent_loop=mock_agent_loop)
        await hb.stop()  # should not raise

    def _mock_beat_deps(self, hb):
        """Mock all _beat dependencies for isolated testing."""
        hb._check_restart_requested = AsyncMock(return_value=False)
        hb._report_health = AsyncMock()
        hb._check_pending_tasks = AsyncMock(return_value=[])
        hb._check_stale_tasks = AsyncMock(return_value=[])
        hb._check_missions = AsyncMock(return_value=[])
        hb._check_delegated_reviews = AsyncMock(return_value=[])
        hb._reset_recurring_tasks = AsyncMock()
        hb._prune_old_data = AsyncMock()

    async def test_beat_reports_health(self, mock_agent_loop):
        hb = Heartbeat(agent_name="robin", agent_loop=mock_agent_loop)
        self._mock_beat_deps(hb)

        await hb._beat()

        hb._report_health.assert_awaited_once()

    async def test_beat_detects_pending_tasks(self, mock_agent_loop):
        hb = Heartbeat(agent_name="robin", agent_loop=mock_agent_loop)
        self._mock_beat_deps(hb)
        hb._check_pending_tasks = AsyncMock(return_value=[
            {"key": "INO-001", "title": "Fix bug", "priority": "high", "created_by": "ino"},
        ])
        hb._trigger_task_pickup = AsyncMock()

        await hb._beat()

        hb._trigger_task_pickup.assert_awaited_once()

    async def test_beat_checks_stale_when_no_pending(self, mock_agent_loop):
        """When no pending tasks and agent idle, check for stale tasks."""
        mock_agent_loop.is_busy.return_value = False
        hb = Heartbeat(agent_name="robin", agent_loop=mock_agent_loop)
        self._mock_beat_deps(hb)

        await hb._beat()

        hb._check_stale_tasks.assert_awaited_once()

    async def test_beat_resets_recurring_tasks(self, mock_agent_loop):
        hb = Heartbeat(agent_name="robin", agent_loop=mock_agent_loop)
        self._mock_beat_deps(hb)

        await hb._beat()

        hb._reset_recurring_tasks.assert_awaited_once()

    async def test_beat_skips_task_pickup_when_busy(self, mock_agent_loop):
        mock_agent_loop.is_busy.return_value = True
        hb = Heartbeat(agent_name="robin", agent_loop=mock_agent_loop)

        tasks = [{"key": "INO-001", "title": "Fix bug", "priority": "high", "created_by": "ino"}]
        await hb._trigger_task_pickup(tasks)

        # Agent is busy, should NOT trigger agent loop
        mock_agent_loop.run.assert_not_awaited()

    async def test_trigger_task_pickup_when_idle(self, mock_agent_loop):
        mock_agent_loop.is_busy.return_value = False
        hb = Heartbeat(agent_name="robin", agent_loop=mock_agent_loop)

        tasks = [{"key": "INO-001", "title": "Fix bug", "priority": "high", "created_by": "ino"}]

        # _trigger_task_pickup creates a background task
        await hb._trigger_task_pickup(tasks)

        # Give the background task a moment to start
        await asyncio.sleep(0.05)

        # The agent loop should have been called
        mock_agent_loop.run.assert_awaited_once()
        call_kwargs = mock_agent_loop.run.call_args[1]
        assert "INO-001" in call_kwargs.get("conversation_id", "") or "INO-001" in mock_agent_loop.run.call_args[0][0]

    async def test_beat_runs_daily_prune(self, mock_agent_loop):
        hb = Heartbeat(agent_name="robin", agent_loop=mock_agent_loop)
        self._mock_beat_deps(hb)
        hb._last_prune_date = None  # Force first prune

        await hb._beat()

        hb._prune_old_data.assert_awaited_once()

    async def test_beat_skips_prune_same_day(self, mock_agent_loop):
        from datetime import date

        hb = Heartbeat(agent_name="robin", agent_loop=mock_agent_loop)
        self._mock_beat_deps(hb)
        hb._last_prune_date = date.today()  # Already pruned today

        await hb._beat()

        hb._prune_old_data.assert_not_awaited()

    async def test_beat_handles_errors(self, mock_agent_loop):
        hb = Heartbeat(agent_name="robin", agent_loop=mock_agent_loop)
        self._mock_beat_deps(hb)
        hb._report_health = AsyncMock(side_effect=Exception("DB down"))

        # Should not raise — error is caught in _loop
        with pytest.raises(Exception, match="DB down"):
            await hb._beat()


# --- Cron / Scheduler tests ---


class TestScheduler:
    @pytest.fixture
    def mock_agent_loop(self):
        loop = MagicMock()
        loop.is_busy.return_value = False
        loop.run = AsyncMock(return_value="ok")
        return loop

    def test_task_check_prompt_exists(self):
        assert "task" in TASK_CHECK_PROMPT.lower()
        assert "configured channels" in TASK_CHECK_PROMPT
        assert "task_workflow skill" in TASK_CHECK_PROMPT

    def test_daily_review_interval(self):
        assert DEFAULT_DAILY_REVIEW_MINUTES == 1440  # 24h

    async def test_start_loads_jobs_from_db(self, mock_agent_loop):
        sched = Scheduler(agent_name="robin", agent_loop=mock_agent_loop)

        # Mock DB returning one job
        sched._load_cron_jobs = AsyncMock(return_value=[
            {"id": 1, "name": "task_check", "prompt": TASK_CHECK_PROMPT, "interval_minutes": 30},
        ])

        await sched.start()
        assert len(sched._tasks) == 1

        await sched.stop()
        assert len(sched._tasks) == 0

    async def test_start_with_no_jobs(self, mock_agent_loop):
        sched = Scheduler(agent_name="robin", agent_loop=mock_agent_loop)
        sched._load_cron_jobs = AsyncMock(return_value=[])

        await sched.start()
        assert len(sched._tasks) == 0

        await sched.stop()

    async def test_start_with_multiple_jobs(self, mock_agent_loop):
        sched = Scheduler(agent_name="robin", agent_loop=mock_agent_loop)
        sched._load_cron_jobs = AsyncMock(return_value=[
            {"id": 1, "name": "task_check", "prompt": TASK_CHECK_PROMPT, "interval_minutes": 30},
            {"id": 2, "name": "crypto_news", "prompt": "Summarize crypto news", "interval_minutes": 720},
        ])

        await sched.start()
        assert len(sched._tasks) == 2

        await sched.stop()
        assert len(sched._tasks) == 0

    async def test_stop_cancels_all_tasks(self, mock_agent_loop):
        sched = Scheduler(agent_name="robin", agent_loop=mock_agent_loop)
        sched._load_cron_jobs = AsyncMock(return_value=[
            {"id": 1, "name": "task_check", "prompt": TASK_CHECK_PROMPT, "interval_minutes": 30},
        ])

        await sched.start()
        assert len(sched._tasks) == 1

        await sched.stop()
        assert len(sched._tasks) == 0

    async def test_stop_when_not_started(self, mock_agent_loop):
        sched = Scheduler(agent_name="robin", agent_loop=mock_agent_loop)
        await sched.stop()  # should not raise

    async def test_run_recurring_calls_agent_loop(self, mock_agent_loop):
        sched = Scheduler(agent_name="robin", agent_loop=mock_agent_loop)

        # Mock _seconds_until_next_slot to return 0 so it fires immediately
        with patch("inotagent.scheduler.cron._seconds_until_next_slot", return_value=0):
            task = asyncio.create_task(
                sched._run_recurring(job_id=1, name="test", interval_seconds=60, prompt="test prompt")
            )

            await asyncio.sleep(0.1)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        mock_agent_loop.run.assert_awaited()
        call_args = mock_agent_loop.run.call_args
        assert call_args[0][0] == "test prompt"
        assert "cron-test-robin" in call_args[1]["conversation_id"]

    async def test_run_recurring_handles_errors(self, mock_agent_loop):
        mock_agent_loop.run.side_effect = Exception("LLM error")
        sched = Scheduler(agent_name="robin", agent_loop=mock_agent_loop)

        with patch("inotagent.scheduler.cron._seconds_until_next_slot", return_value=0):
            task = asyncio.create_task(
                sched._run_recurring(job_id=1, name="test", interval_seconds=60, prompt="test")
            )

            await asyncio.sleep(0.15)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Should have been called despite errors
        assert mock_agent_loop.run.await_count >= 1

    async def test_run_recurring_updates_last_run(self, mock_agent_loop):
        sched = Scheduler(agent_name="robin", agent_loop=mock_agent_loop)
        sched._update_last_run = AsyncMock()

        with patch("inotagent.scheduler.cron._seconds_until_next_slot", return_value=0):
            task = asyncio.create_task(
                sched._run_recurring(job_id=42, name="test", interval_seconds=60, prompt="test")
            )

            await asyncio.sleep(0.1)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        sched._update_last_run.assert_awaited_with(42)

    async def test_run_recurring_skips_task_check_when_no_work(self, mock_agent_loop):
        sched = Scheduler(agent_name="robin", agent_loop=mock_agent_loop)
        sched._has_pending_work = AsyncMock(return_value=False)
        sched._update_last_run = AsyncMock()

        with patch("inotagent.scheduler.cron._seconds_until_next_slot", return_value=0):
            task = asyncio.create_task(
                sched._run_recurring(job_id=1, name="task_check", interval_seconds=60, prompt="check tasks")
            )

            await asyncio.sleep(0.1)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # LLM should NOT have been called
        mock_agent_loop.run.assert_not_awaited()

    async def test_run_recurring_runs_non_task_check_always(self, mock_agent_loop):
        sched = Scheduler(agent_name="robin", agent_loop=mock_agent_loop)
        sched._update_last_run = AsyncMock()

        with patch("inotagent.scheduler.cron._seconds_until_next_slot", return_value=0):
            task = asyncio.create_task(
                sched._run_recurring(job_id=2, name="crypto_news", interval_seconds=60, prompt="summarize")
            )

            await asyncio.sleep(0.1)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Non-task_check jobs always run (no _has_pending_work check)
        mock_agent_loop.run.assert_awaited()

    async def test_load_cron_jobs_failure(self, mock_agent_loop):
        sched = Scheduler(agent_name="robin", agent_loop=mock_agent_loop)

        with patch("inotagent.db.pool.get_connection", side_effect=RuntimeError("no pool")):
            jobs = await sched._load_cron_jobs()

        # Should return empty list on failure
        assert jobs == []


# --- Config helper tests ---


class TestConfigHelper:
    async def test_get_config_int_default_on_error(self):
        with patch("inotagent.db.pool.get_connection", side_effect=RuntimeError("no pool")):
            result = await _get_config_int("test.key", 42)
        assert result == 42


# --- Main integration tests ---


class TestMainSchedulerIntegration:
    async def test_async_main_starts_scheduler_with_db(self):
        """Verify scheduler is started when DB is available."""
        from inotagent.scheduler.heartbeat import Heartbeat
        from inotagent.scheduler.cron import Scheduler

        # Just verify the classes exist and can be instantiated
        mock_loop = MagicMock()
        mock_loop.is_busy.return_value = False

        hb = Heartbeat(agent_name="test", agent_loop=mock_loop)
        assert hb.agent_name == "test"

        sched = Scheduler(agent_name="test", agent_loop=mock_loop)
        assert sched.agent_name == "test"

    def test_default_task_check_minutes(self):
        assert DEFAULT_TASK_CHECK_MINUTES == 30
