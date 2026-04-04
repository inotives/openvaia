"""Base poller with retry, health heartbeat, and cycle management."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

STATUS_FILE = Path("/opt/inotagent-trading/.poller_status.json")
# Fallback for local dev
LOCAL_STATUS_FILE = Path(__file__).parent.parent / ".poller_status.json"


def _status_path() -> Path:
    if STATUS_FILE.parent.exists():
        return STATUS_FILE
    return LOCAL_STATUS_FILE


class BasePoller:
    """Base class for all pollers with retry, health, and cycle timing."""

    name: str = "base"
    max_retries: int = 3
    backoff_base: float = 1.0  # 1s, 4s, 16s

    def __init__(self, interval: int = 60) -> None:
        self.interval = interval
        self._error_count_1h: int = 0
        self._last_error_reset: float = time.monotonic()

    async def setup(self) -> None:
        """Override to initialize connections, pools, etc."""

    async def cycle(self) -> None:
        """Override with the main work for each poll cycle."""
        raise NotImplementedError

    async def teardown(self) -> None:
        """Override to clean up resources."""

    async def run(self) -> None:
        """Main loop — run cycles forever with retry and health."""
        logger.info(f"[{self.name}] Starting poller (interval={self.interval}s)")
        await self.setup()

        try:
            while True:
                cycle_start = time.monotonic()

                success = await self._run_cycle_with_retry()
                self._write_health(success)

                # Reset hourly error counter
                if time.monotonic() - self._last_error_reset > 3600:
                    self._error_count_1h = 0
                    self._last_error_reset = time.monotonic()

                # Sleep remaining interval (skip if cycle took longer)
                elapsed = time.monotonic() - cycle_start
                sleep_time = max(0, self.interval - elapsed)
                if sleep_time == 0:
                    logger.warning(f"[{self.name}] Cycle took {elapsed:.1f}s > interval {self.interval}s, skipping sleep")
                else:
                    await asyncio.sleep(sleep_time)
        except asyncio.CancelledError:
            logger.info(f"[{self.name}] Poller cancelled")
        finally:
            await self.teardown()

    async def _run_cycle_with_retry(self) -> bool:
        """Run cycle with exponential backoff retry. Returns True on success."""
        for attempt in range(self.max_retries):
            try:
                await self.cycle()
                return True
            except Exception as e:
                self._error_count_1h += 1
                wait = self.backoff_base * (4 ** attempt)  # 1s, 4s, 16s
                logger.error(
                    f"[{self.name}] Cycle failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries - 1:
                    logger.info(f"[{self.name}] Retrying in {wait:.0f}s")
                    await asyncio.sleep(wait)

        logger.error(f"[{self.name}] All {self.max_retries} retries failed, skipping cycle")
        return False

    def _write_health(self, success: bool) -> None:
        """Write health status to shared JSON file."""
        try:
            path = _status_path()
            status = {}
            if path.exists():
                try:
                    status = json.loads(path.read_text())
                except (json.JSONDecodeError, OSError):
                    status = {}

            now = datetime.now(timezone.utc).isoformat()
            entry = status.get(self.name, {})

            if success:
                entry["status"] = "ok"
                entry["last_success"] = now
            else:
                entry["status"] = "error"
                entry["last_error"] = now

            entry["errors_1h"] = self._error_count_1h
            entry["updated_at"] = now
            status[self.name] = entry

            path.write_text(json.dumps(status, indent=2))
        except Exception as e:
            logger.debug(f"[{self.name}] Failed to write health status: {e}")
