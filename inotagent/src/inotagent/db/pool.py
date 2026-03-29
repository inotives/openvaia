"""Async Postgres connection pool via psycopg3."""

from __future__ import annotations

import logging
import os
import re
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)

_pool: AsyncConnectionPool | None = None


def _build_conninfo() -> str:
    """Build connection string from environment variables."""
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "inotives")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "")
    return f"host={host} port={port} dbname={db} user={user} password={password}"


async def init_pool(conninfo: str | None = None, min_size: int = 2, max_size: int = 10) -> None:
    """Initialize the global connection pool."""
    global _pool
    if _pool is not None:
        return

    info = conninfo or _build_conninfo()
    _pool = AsyncConnectionPool(
        conninfo=info,
        min_size=min_size,
        max_size=max_size,
        kwargs={"row_factory": dict_row, "autocommit": True},
    )
    await _pool.open()
    logger.info("Database pool initialized")


async def close_pool() -> None:
    """Close the global connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database pool closed")


@asynccontextmanager
async def get_connection() -> AsyncGenerator[AsyncConnection, None]:
    """Get a connection from the pool."""
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_pool() first.")
    async with _pool.connection() as conn:
        yield conn


_SCHEMA_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")


def get_schema() -> str:
    """Get the platform schema name. Validated to prevent SQL injection."""
    schema = os.environ.get("PLATFORM_SCHEMA", "platform")
    if not _SCHEMA_PATTERN.match(schema):
        raise ValueError(f"Invalid PLATFORM_SCHEMA: {schema!r} (must be lowercase alphanumeric + underscores)")
    return schema
