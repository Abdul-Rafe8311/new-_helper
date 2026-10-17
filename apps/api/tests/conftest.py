"""Shared fixtures.

DB tests run against TEST_DATABASE_URL (the pgvector service container in CI) and are
skipped when it is unset. Each test runs inside a transaction that is rolled back, so
nothing persists. Set TEST_DB_SCHEMA (must start with "test") to isolate the tables in
their own schema on a shared database; that schema is dropped afterwards. Tests refuse
to run against a Supabase database's public schema.
"""

import os
import re
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.config import Settings
from app.db.session import build_engine, get_session
from app.main import create_app
from app.models import Base  # importing app.models registers every table

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
TEST_DB_SCHEMA = os.environ.get("TEST_DB_SCHEMA")

TEST_SETTINGS = Settings(
    env="test",
    jwt_secret="j" * 64,
    cron_secret="c" * 64,
    demo_email="demo@newshelper.test",
)


def _check_target() -> None:
    if TEST_DB_SCHEMA is not None and not re.fullmatch(r"test[a-z0-9_]*", TEST_DB_SCHEMA):
        pytest.exit("TEST_DB_SCHEMA must match test[a-z0-9_]*", returncode=2)
    if TEST_DATABASE_URL and "supabase" in TEST_DATABASE_URL and not TEST_DB_SCHEMA:
        pytest.exit("Refusing to run DB tests in Supabase's public schema", returncode=2)


@pytest.fixture(scope="session")
async def engine() -> AsyncIterator[AsyncEngine]:
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set")
    _check_target()
    search_path = f"{TEST_DB_SCHEMA}, public" if TEST_DB_SCHEMA else None
    eng = build_engine(TEST_DATABASE_URL, search_path=search_path)
    async with eng.begin() as conn:
        if TEST_DB_SCHEMA:
            await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{TEST_DB_SCHEMA}"'))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector SCHEMA public"))
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    if TEST_DB_SCHEMA:
        async with eng.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{TEST_DB_SCHEMA}" CASCADE'))
    await eng.dispose()


@pytest.fixture
async def db(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """A session whose commits become savepoints inside one rolled-back transaction."""
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(
            bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


@pytest.fixture
async def client(db: AsyncSession) -> AsyncIterator[AsyncClient]:
    api = create_app(TEST_SETTINGS)

    async def _session() -> AsyncIterator[AsyncSession]:
        yield db

    api.dependency_overrides[get_session] = _session
    async with AsyncClient(transport=ASGITransport(app=api), base_url="http://test") as c:
        yield c
