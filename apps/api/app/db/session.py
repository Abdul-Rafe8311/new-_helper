"""Async database engine and session factory.

Supabase is reached through its connection pooler, which breaks asyncpg's
prepared-statement cache, so the cache is always disabled.
"""

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

ASYNCPG_CONNECT_ARGS: dict[str, Any] = {"statement_cache_size": 0}


def build_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(
        database_url,
        connect_args=dict(ASYNCPG_CONNECT_ARGS),
        pool_pre_ping=True,
    )


@lru_cache
def get_engine() -> AsyncEngine:
    return build_engine(get_settings().database_url)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding one session per request."""
    async with get_sessionmaker()() as session:
        yield session
