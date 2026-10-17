"""Checks against a real Postgres + pgvector (the CI service container).

Skipped unless TEST_DATABASE_URL is set, so local runs never touch Supabase.
"""

import os

import pytest
from sqlalchemy import text

from app.db.session import build_engine

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL not set"),
]


async def test_pgvector_extension_available() -> None:
    assert TEST_DATABASE_URL is not None
    engine = build_engine(TEST_DATABASE_URL)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            distance = await conn.scalar(text("SELECT '[1,0,0]'::vector <=> '[0,1,0]'::vector"))
        assert distance == pytest.approx(1.0)
    finally:
        await engine.dispose()
