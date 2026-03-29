"""Per-agent environment loader — reads agents/{name}/.env into a dict."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_agent_env(env_path: Path) -> dict[str, str]:
    """Load a .env file into a dict. Falls back to empty dict if file missing."""
    env: dict[str, str] = {}
    if not env_path.exists():
        logger.warning(f"Agent .env not found: {env_path}")
        return env

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip surrounding quotes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key:
            env[key] = value

    logger.info(f"Loaded {len(env)} env vars from {env_path.name}")
    return env
