"""Tests for poller base — retry logic, health heartbeat, cycle timing."""

import asyncio
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from poller.base import BasePoller


class SuccessPoller(BasePoller):
    name = "test_success"

    def __init__(self):
        super().__init__(interval=1)
        self.cycle_count = 0

    async def cycle(self):
        self.cycle_count += 1


class FailPoller(BasePoller):
    name = "test_fail"

    def __init__(self):
        super().__init__(interval=1)
        self.attempt_count = 0

    async def cycle(self):
        self.attempt_count += 1
        raise RuntimeError("simulated failure")


class FailThenSucceedPoller(BasePoller):
    name = "test_flaky"

    def __init__(self, fail_count: int = 2):
        super().__init__(interval=1)
        self.attempt_count = 0
        self.fail_count = fail_count

    async def cycle(self):
        self.attempt_count += 1
        if self.attempt_count <= self.fail_count:
            raise RuntimeError(f"fail #{self.attempt_count}")


class TestRetry:
    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        poller = SuccessPoller()
        result = await poller._run_cycle_with_retry()
        assert result is True
        assert poller.cycle_count == 1

    @pytest.mark.asyncio
    async def test_fail_retries_max_times(self):
        poller = FailPoller()
        poller.backoff_base = 0.01  # fast for tests
        result = await poller._run_cycle_with_retry()
        assert result is False
        assert poller.attempt_count == 3  # max_retries

    @pytest.mark.asyncio
    async def test_fail_then_succeed(self):
        poller = FailThenSucceedPoller(fail_count=2)
        poller.backoff_base = 0.01
        result = await poller._run_cycle_with_retry()
        assert result is True
        assert poller.attempt_count == 3  # 2 fails + 1 success

    @pytest.mark.asyncio
    async def test_error_count_increments(self):
        poller = FailPoller()
        poller.backoff_base = 0.01
        await poller._run_cycle_with_retry()
        assert poller._error_count_1h == 3


class TestHealthHeartbeat:
    @pytest.mark.asyncio
    async def test_writes_success_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            status_file = Path(tmpdir) / ".poller_status.json"
            with patch("poller.base._status_path", return_value=status_file):
                poller = SuccessPoller()
                poller._write_health(success=True)

                status = json.loads(status_file.read_text())
                assert status["test_success"]["status"] == "ok"
                assert "last_success" in status["test_success"]

    @pytest.mark.asyncio
    async def test_writes_error_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            status_file = Path(tmpdir) / ".poller_status.json"
            with patch("poller.base._status_path", return_value=status_file):
                poller = FailPoller()
                poller._error_count_1h = 5
                poller._write_health(success=False)

                status = json.loads(status_file.read_text())
                assert status["test_fail"]["status"] == "error"
                assert status["test_fail"]["errors_1h"] == 5

    @pytest.mark.asyncio
    async def test_multiple_pollers_coexist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            status_file = Path(tmpdir) / ".poller_status.json"
            with patch("poller.base._status_path", return_value=status_file):
                p1 = SuccessPoller()
                p1.name = "public"
                p1._write_health(success=True)

                p2 = FailPoller()
                p2.name = "private"
                p2._write_health(success=False)

                status = json.loads(status_file.read_text())
                assert status["public"]["status"] == "ok"
                assert status["private"]["status"] == "error"


class TestRunLoop:
    @pytest.mark.asyncio
    async def test_run_executes_cycles(self):
        poller = SuccessPoller()
        poller.interval = 0.01

        async def stop_after_3():
            while poller.cycle_count < 3:
                await asyncio.sleep(0.01)
            raise asyncio.CancelledError

        with patch("poller.base._status_path", return_value=Path("/dev/null")):
            try:
                task = asyncio.create_task(poller.run())
                await asyncio.wait_for(stop_after_3(), timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        assert poller.cycle_count >= 3
