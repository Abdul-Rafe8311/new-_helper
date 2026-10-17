from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Article, Edition, EventType, ReaderEvent, Source
from app.scripts.seed import seed_demo_user, seed_sources
from app.sources.registry import load_registry
from tests.conftest import TEST_SETTINGS
from tests.factories import make_article, make_source, make_user

pytestmark = pytest.mark.integration


def _unit(i: int) -> list[float]:
    vec = [0.0] * 384
    vec[i] = 1.0
    return vec


async def test_article_embedding_cosine_search(db: AsyncSession) -> None:
    source = await make_source(db)
    near = await make_article(db, source_id=source.id, embedding=_unit(0))
    await make_article(db, source_id=source.id, embedding=_unit(1))
    result = await db.execute(
        select(Article.id).order_by(Article.embedding.cosine_distance(_unit(0))).limit(1)
    )
    assert result.scalar_one() == near.id


async def test_edition_unique_per_user_and_day(db: AsyncSession) -> None:
    user = await make_user(db)
    db.add(Edition(user_id=user.id, edition_date=date(2026, 10, 17), number=1))
    await db.flush()
    db.add(Edition(user_id=user.id, edition_date=date(2026, 10, 17), number=2))
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_reader_event_defaults(db: AsyncSession) -> None:
    user = await make_user(db)
    event = ReaderEvent(user_id=user.id, type=EventType.OPEN)
    db.add(event)
    await db.flush()
    await db.refresh(event)
    assert event.meta == {}
    assert event.created_at is not None


async def test_seed_is_idempotent(db: AsyncSession) -> None:
    specs = load_registry()
    assert await seed_sources(db, specs) == len(specs)
    assert await seed_sources(db, specs) == len(specs)
    assert await db.scalar(select(func.count()).select_from(Source)) == len(specs)
    assert await seed_demo_user(db, TEST_SETTINGS) is True
    assert await seed_demo_user(db, TEST_SETTINGS) is False


def test_registry_is_valid_and_sized() -> None:
    specs = load_registry()
    assert 35 <= len(specs) <= 50
    assert all(s.url.startswith("https://") for s in specs)
