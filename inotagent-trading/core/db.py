"""Database connections for the trading toolkit.

Provides:
- async_pool()  — asyncpg pool for pollers (async)
- sync_connect() — psycopg connection for CLI (sync)
- schema()      — qualified schema name for SQL
"""

from __future__ import annotations

import re
from contextlib import asynccontextmanager, contextmanager

import asyncpg
import psycopg
from psycopg.rows import dict_row

from core.config import settings

_SCHEMA_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")
_async_pool: asyncpg.Pool | None = None


def schema() -> str:
    """Return the trading schema name, validated as a safe SQL identifier."""
    s = settings.trading_schema
    if not _SCHEMA_PATTERN.match(s):
        raise ValueError(f"Invalid schema name: {s!r}")
    return s


# ── Async (pollers) ──────────────────────────────────────────────────────────


async def get_async_pool() -> asyncpg.Pool:
    """Get or create the asyncpg connection pool."""
    global _async_pool
    if _async_pool is None:
        _async_pool = await asyncpg.create_pool(
            host=settings.postgres_host,
            port=settings.postgres_port,
            user=settings.postgres_user,
            password=settings.postgres_password,
            database=settings.postgres_db,
            min_size=2,
            max_size=10,
        )
    return _async_pool


async def close_async_pool() -> None:
    global _async_pool
    if _async_pool is not None:
        await _async_pool.close()
        _async_pool = None


@asynccontextmanager
async def async_conn():
    """Async context manager — yields an asyncpg connection from the pool."""
    pool = await get_async_pool()
    async with pool.acquire() as conn:
        yield conn


# ── Sync (CLI) ───────────────────────────────────────────────────────────────


@contextmanager
def sync_connect():
    """Sync context manager — yields a psycopg connection with dict rows."""
    with psycopg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        dbname=settings.postgres_db,
        row_factory=dict_row,
        autocommit=False,
    ) as conn:
        yield conn
