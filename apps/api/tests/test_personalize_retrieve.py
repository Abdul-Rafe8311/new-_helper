from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embedder import FakeEmbedder
from app.models import (
    Article,
    Edition,
    EditionItem,
    EditionStatus,
    EventType,
    ReaderEvent,
    Slot,
    User,
)
from app.personalize.profile import profile_view
from app.personalize.retrieve import previously_seen, retrieve_candidates
from app.personalize.types import Candidate, ProfileView
from tests.factories import make_article, make_source, make_user

NOW = datetime(2026, 10, 17, 6, 0, tzinfo=UTC)
TODAY = NOW.date()
E = FakeEmbedder()


async def story(db: AsyncSession, title: str, *, hours_old: float = 2, **over: Any) -> Article:
    fields: dict[str, Any] = {
        "title": title,
        "headline": title,
        "summary": f"{title} summary.",
        "published_at": NOW - timedelta(hours=hours_old),
        "embedding": E.embed([title])[0],
        "cluster_size": 1,
    }
    fields.update(over)
    return await make_article(db, **fields)


async def reader(db: AsyncSession, **profile: Any) -> tuple[User, ProfileView]:
    user = await make_user(db, profile=profile)
    return user, profile_view(user, user.profile)


async def retrieve(db: AsyncSession, view: ProfileView, day: date = TODAY) -> list[Candidate]:
    return await retrieve_candidates(db, view, day, now=NOW)


@pytest.mark.integration
async def test_vector_arm_finds_semantic_neighbours_and_skips_unsummarised_and_stale(
    db: AsyncSession,
) -> None:
    near = await story(db, "Agents ship")
    await story(db, "Old news", hours_old=30)
    await story(db, "No summary here", summary=None)
    _user, view = await reader(db, interest_vector=E.embed(["Agents ship"])[0])
    got = await retrieve(db, view)
    assert [c.id for c in got] == [near.id]
    assert got[0].origins == {"vector"}


@pytest.mark.integration
async def test_keyword_arm_matches_full_text_without_a_vector(db: AsyncSession) -> None:
    hit = await story(db, "Lahore Qalandars win the PSL opener", embedding=None)
    await story(db, "Parliament debates budget", embedding=None)
    _user, view = await reader(db, keywords=["PSL"], entities={"teams": ["Lahore Qalandars"]})
    got = await retrieve(db, view)
    assert [c.id for c in got] == [hit.id]
    assert got[0].origins == {"keyword"}


@pytest.mark.integration
async def test_big_story_arm_adds_multi_outlet_clusters(db: AsyncSession) -> None:
    big = await story(db, "Summit ends in deal", cluster_id=7, cluster_size=9, embedding=None)
    await story(db, "Local bake sale", cluster_size=1, embedding=None)
    _user, view = await reader(db)
    got = await retrieve(db, view)
    assert [c.id for c in got] == [big.id]
    assert got[0].origins == {"big_story"}
    assert got[0].cluster_size == 9


@pytest.mark.integration
async def test_arms_are_unioned_and_origins_merge(db: AsyncSession) -> None:
    both = await story(db, "PSL final preview", cluster_id=3, cluster_size=4)
    _user, view = await reader(
        db, keywords=["PSL"], interest_vector=E.embed(["PSL final preview"])[0]
    )
    [c] = await retrieve(db, view)
    assert c.id == both.id
    assert c.origins == {"vector", "keyword", "big_story"}


@pytest.mark.integration
async def test_blocked_topics_keywords_and_sources_are_excluded(db: AsyncSession) -> None:
    bad_src = await make_source(db, name="Gossip Daily")
    good = await story(db, "Chip export rules tighten", topics={"ai": 0.8})
    await story(db, "Celebrity wedding", topics={"celebrity": 0.9})
    await story(db, "Transfer rumours swirl")
    await story(db, "Quiet article", source_id=bad_src.id)
    vec = E.embed(["Chip export rules tighten"])[0]
    _user, view = await reader(
        db,
        interest_vector=vec,
        blocked={"topics": ["celebrity"], "keywords": ["rumours"], "sources": ["gossip daily"]},
    )
    assert [c.id for c in await retrieve(db, view)] == [good.id]


@pytest.mark.integration
async def test_articles_and_stories_from_the_last_seven_editions_are_excluded(
    db: AsyncSession,
) -> None:
    printed = await story(db, "Printed yesterday", cluster_id=11)
    same_story = await story(db, "Same story other outlet", cluster_id=11)
    fresh = await story(db, "Fresh today", cluster_id=12)
    old = await story(db, "Printed eight days ago", cluster_id=13)
    user, view = await reader(db, interest_vector=E.embed(["Fresh today"])[0])
    for days_ago, article in ((1, printed), (8, old)):
        edition = Edition(
            user_id=user.id,
            edition_date=TODAY - timedelta(days=days_ago),
            number=days_ago,
            status=EditionStatus.READY,
        )
        db.add(edition)
        await db.flush()
        db.add(
            EditionItem(
                edition_id=edition.id,
                article_id=article.id,
                section="s",
                position=0,
                slot=Slot.LEAD,
            )
        )
    await db.flush()
    ids = {c.id for c in await retrieve(db, view)}
    assert {fresh.id, old.id} <= ids
    assert not {printed.id, same_story.id} & ids


@pytest.mark.integration
async def test_editions_dated_today_do_not_exclude_so_regeneration_can_reuse_items(
    db: AsyncSession,
) -> None:
    a = await story(db, "Already in today's paper")
    user, view = await reader(db, interest_vector=E.embed(["Already in today's paper"])[0])
    edition = Edition(user_id=user.id, edition_date=TODAY, number=1, status=EditionStatus.READY)
    db.add(edition)
    await db.flush()
    db.add(
        EditionItem(edition_id=edition.id, article_id=a.id, section="s", position=0, slot=Slot.LEAD)
    )
    await db.flush()
    assert [c.id for c in await retrieve(db, view)] == [a.id]


@pytest.mark.integration
async def test_previously_seen_uses_impressions_opens_and_skips(db: AsyncSession) -> None:
    a = await story(db, "s0")
    b = await story(db, "s1")
    c = await story(db, "s2")
    user, _ = await reader(db)
    for article, kind in ((a, EventType.IMPRESSION), (b, EventType.SKIP), (c, EventType.SAVE)):
        db.add(ReaderEvent(user_id=user.id, article_id=article.id, type=kind))
    await db.flush()
    assert await previously_seen(db, user.id) == {a.id, b.id}
