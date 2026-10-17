"""The reader endpoints: event batches, the /r redirect, story state, saved stories, the archive."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_background_sessionmaker
from app.api.routers.events import events_limiter
from app.core.ratelimit import SlidingWindowLimiter
from app.db.session import get_session
from app.main import create_app
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
from tests.conftest import TEST_SETTINGS
from tests.editions_helpers import sessionmaker_for
from tests.factories import DEFAULT_PASSWORD, make_article, make_source, make_user

pytestmark = pytest.mark.integration

DAY = datetime(2026, 10, 17, tzinfo=UTC).date()


@pytest.fixture
async def api(db: AsyncSession) -> AsyncIterator[AsyncClient]:
    app = create_app(TEST_SETTINGS)

    async def _session() -> AsyncIterator[AsyncSession]:
        yield db

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_background_sessionmaker] = lambda: sessionmaker_for(db)
    app.dependency_overrides[events_limiter] = lambda: SlidingWindowLimiter(100, 60)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def sign_in(client: AsyncClient, db: AsyncSession, email: str = "reader@example.com") -> User:
    user = await make_user(db, email=email, timezone="UTC")
    response = await client.post("/auth/login", json={"email": email, "password": DEFAULT_PASSWORD})
    assert response.status_code == 200
    return user


async def seed_edition(
    db: AsyncSession, user: User, *, day: Any = DAY, urls: tuple[str, ...] = ("a", "b", "c")
) -> list[EditionItem]:
    source = await make_source(db, name="The Wire")
    edition = Edition(
        user_id=user.id,
        edition_date=day,
        number=1,
        status=EditionStatus.READY,
        title="Paper",
        stats={"items": len(urls), "top_topics": ["AI", "Cricket", "Space", "Food"]},
    )
    db.add(edition)
    await db.flush()
    items = []
    for position, name in enumerate(urls):
        article = await make_article(
            db,
            url=name if ":" in name else f"https://example.com/{edition.id}/{name}",
            source_id=source.id,
            key_facts=[{"text": "A fact"}, "Another fact"],
        )
        item = EditionItem(
            edition_id=edition.id,
            article_id=article.id,
            section="Tech",
            position=position,
            slot=Slot.STANDARD,
            headline=f"Headline {name}",
            summary="Summary",
        )
        db.add(item)
        items.append(item)
    await db.flush()
    return items


def event(item: EditionItem, kind: str, **extra: Any) -> dict[str, Any]:
    return {"type": kind, "edition_item_id": str(item.id), **extra}


async def stored(db: AsyncSession) -> list[ReaderEvent]:
    return list((await db.scalars(select(ReaderEvent).order_by(ReaderEvent.created_at))).all())


async def test_routes_need_a_session(api: AsyncClient) -> None:
    some = "00000000-0000-4000-8000-000000000001"
    assert (await api.post("/events", json={"events": []})).status_code == 401
    assert (await api.get(f"/r/{some}")).status_code == 401
    assert (await api.get("/saved")).status_code == 401


async def test_event_batches_are_stored_against_the_readers_own_stories(
    api: AsyncClient, db: AsyncSession
) -> None:
    user = await sign_in(api, db)
    first, second, _ = await seed_edition(db, user)
    response = await api.post(
        "/events",
        json={
            "events": [
                event(first, "impression", meta={"view": "cards"}),
                event(first, "dwell", value=12.5),
                event(second, "skip"),
            ]
        },
    )
    assert response.status_code == 200
    assert response.json() == {"accepted": 3, "rejected": 0}
    rows = await stored(db)
    assert {r.type for r in rows} == {EventType.IMPRESSION, EventType.DWELL, EventType.SKIP}
    dwell = next(r for r in rows if r.type is EventType.DWELL)
    assert dwell.value == 12.5
    assert dwell.user_id == user.id
    assert dwell.edition_item_id == first.id
    assert dwell.article_id == first.article_id  # filled in from the story, not the client
    assert dwell.edition_id == first.edition_id


async def test_events_for_someone_elses_stories_are_dropped(
    api: AsyncClient, db: AsyncSession
) -> None:
    other = await make_user(db, email="other@example.com")
    foreign, *_ = await seed_edition(db, other)
    user = await sign_in(api, db)
    mine, *_ = await seed_edition(db, user, day=DAY - timedelta(days=1))
    response = await api.post(
        "/events", json={"events": [event(foreign, "save"), event(mine, "save")]}
    )
    assert response.json() == {"accepted": 1, "rejected": 1}
    assert [r.edition_item_id for r in await stored(db)] == [mine.id]


@pytest.mark.parametrize(
    "body",
    [
        {"events": []},
        {
            "events": [
                {"type": "pdf_download", "edition_item_id": "00000000-0000-4000-8000-000000000001"}
            ]
        },
        {"events": [{"type": "dwell", "edition_item_id": "nope"}]},
        {
            "events": [
                {
                    "type": "dwell",
                    "edition_item_id": "00000000-0000-4000-8000-000000000001",
                    "value": 99999,
                }
            ]
        },
        {
            "events": [
                {
                    "type": "dwell",
                    "edition_item_id": "00000000-0000-4000-8000-000000000001",
                    "value": -1,
                }
            ]
        },
        {
            "events": [
                {
                    "type": "save",
                    "edition_item_id": "00000000-0000-4000-8000-000000000001",
                    "meta": {"k": "x" * 201},
                }
            ]
        },
    ],
)
async def test_bad_batches_are_refused(
    api: AsyncClient, db: AsyncSession, body: dict[str, Any]
) -> None:
    await sign_in(api, db)
    assert (await api.post("/events", json=body)).status_code == 422


async def test_a_batch_is_capped_at_100_events(api: AsyncClient, db: AsyncSession) -> None:
    user = await sign_in(api, db)
    item, *_ = await seed_edition(db, user)
    too_many = {"events": [event(item, "impression")] * 101}
    assert (await api.post("/events", json=too_many)).status_code == 422
    assert (
        await api.post("/events", json={"events": [event(item, "impression")] * 100})
    ).status_code == 200


async def test_too_many_batches_are_rate_limited(db: AsyncSession) -> None:
    app = create_app(TEST_SETTINGS)

    async def _session() -> AsyncIterator[AsyncSession]:
        yield db

    limiter = SlidingWindowLimiter(limit=2, window_seconds=60)
    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[events_limiter] = lambda: limiter
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        user = await sign_in(client, db)
        item, *_ = await seed_edition(db, user)
        body = {"events": [event(item, "impression")]}
        assert (await client.post("/events", json=body)).status_code == 200
        assert (await client.post("/events", json=body)).status_code == 200
        blocked = await client.post("/events", json=body)
        assert blocked.status_code == 429
        assert blocked.json()["error"]["code"] == "rate_limited"


async def test_read_original_logs_an_open_and_redirects(api: AsyncClient, db: AsyncSession) -> None:
    user = await sign_in(api, db)
    item, *_ = await seed_edition(db, user, urls=("https://news.example.org/story?id=7",))
    response = await api.get(f"/r/{item.id}", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://news.example.org/story?id=7"
    assert response.headers["cache-control"] == "no-store"
    [row] = await stored(db)
    assert (row.type, row.edition_item_id, row.user_id) == (EventType.OPEN, item.id, user.id)


async def test_read_original_refuses_foreign_missing_and_non_http_stories(
    api: AsyncClient, db: AsyncSession
) -> None:
    other = await make_user(db, email="other@example.com")
    foreign, *_ = await seed_edition(db, other)
    user = await sign_in(api, db)
    unsafe, *_ = await seed_edition(
        db, user, day=DAY - timedelta(days=1), urls=("javascript:alert(1)",)
    )
    for target in (foreign.id, unsafe.id, UUID(int=1)):
        response = await api.get(f"/r/{target}", follow_redirects=False)
        assert response.status_code == 404, target
    assert await stored(db) == []


async def test_stories_carry_the_readers_state_and_key_facts(
    api: AsyncClient, db: AsyncSession
) -> None:
    user = await sign_in(api, db)
    a, b, c = await seed_edition(db, user)
    await api.post(
        "/events",
        json={
            "events": [
                event(a, "mark_read"),
                event(a, "save"),
                event(a, "more_like"),
                event(b, "skip"),
                event(b, "skip", value=0),  # undone
                event(b, "less_like"),
                event(b, "more_like"),
                event(b, "more_like", value=0),  # retracting the latest reaction clears it
                event(c, "impression"),
            ]
        },
    )
    await api.get(f"/r/{b.id}", follow_redirects=False)
    items = {i["id"]: i for i in (await api.get(f"/editions/{DAY}")).json()["items"]}
    assert items[str(a.id)]["state"] == {
        "read": True,
        "saved": True,
        "skipped": False,
        "reaction": "more",
    }
    assert items[str(b.id)]["state"] == {
        "read": True,
        "saved": False,
        "skipped": False,
        "reaction": None,
    }
    assert items[str(c.id)]["state"] == {
        "read": False,
        "saved": False,
        "skipped": False,
        "reaction": None,
    }
    assert items[str(a.id)]["key_facts"] == ["A fact", "Another fact"]


async def test_saved_lists_stories_across_editions_newest_save_first(
    api: AsyncClient, db: AsyncSession
) -> None:
    user = await sign_in(api, db)
    a, b, _ = await seed_edition(db, user)
    older, *_ = await seed_edition(db, user, day=DAY - timedelta(days=3))
    assert (await api.get("/saved")).json() == []
    await api.post("/events", json={"events": [event(a, "save")]})
    await api.post("/events", json={"events": [event(older, "save")]})
    await api.post("/events", json={"events": [event(b, "save")]})
    await api.post("/events", json={"events": [event(older, "save", value=0)]})  # un-saved
    saved = (await api.get("/saved")).json()
    assert [s["id"] for s in saved] == [str(b.id), str(a.id)]
    assert saved[0]["edition_date"] == DAY.isoformat()
    assert saved[0]["state"]["saved"] is True
    assert saved[0]["headline"] == "Headline b"


async def test_the_archive_pages_back_through_time(api: AsyncClient, db: AsyncSession) -> None:
    user = await sign_in(api, db)
    for days in range(5):
        await seed_edition(db, user, day=DAY - timedelta(days=days), urls=("x",))
    first = (await api.get("/editions", params={"limit": 2})).json()
    assert [e["date"] for e in first] == [str(DAY), str(DAY - timedelta(days=1))]
    assert first[0]["top_topics"] == ["AI", "Cricket", "Space"]  # at most three chips
    second = (await api.get("/editions", params={"limit": 2, "before": first[-1]["date"]})).json()
    assert [e["date"] for e in second] == [
        str(DAY - timedelta(days=2)),
        str(DAY - timedelta(days=3)),
    ]
    last = (await api.get("/editions", params={"before": second[-1]["date"]})).json()
    assert [e["date"] for e in last] == [str(DAY - timedelta(days=4))]
    assert (await api.get("/editions", params={"limit": 0})).status_code == 422


async def test_a_story_comes_with_the_pictures_and_outlets_of_its_cluster(
    api: AsyncClient, db: AsyncSession
) -> None:
    user = await sign_in(api, db)
    (item, *_) = await seed_edition(db, user, urls=("https://a.example/one",))
    anchor = datetime.now(UTC)
    article = await db.get(Article, item.article_id)
    assert article is not None
    article.cluster_id, article.published_at = 7, anchor
    article.image_url, article.author = "https://img.example/main.jpg", "Sara Khan"
    dawn = await make_source(db, name="Dawn")
    for n, (outlet, image) in enumerate([(dawn, "https://img.example/dawn.jpg"), (dawn, None)]):
        await make_article(
            db,
            url=f"https://dawn.example/{n}",
            source_id=outlet.id,
            cluster_id=7,
            image_url=image,
            published_at=anchor - timedelta(hours=n + 1),
        )
    await make_article(
        db, url="https://old.example/x", cluster_id=7, published_at=anchor - timedelta(days=30)
    )
    await make_article(db, url="https://other.example/y", cluster_id=8, published_at=anchor)

    story = (await api.get(f"/stories/{item.id}")).json()
    assert story["item"]["id"] == str(item.id)
    assert story["edition_date"] == DAY.isoformat()
    assert story["author"] == "Sara Khan"
    assert [i["url"] for i in story["images"]] == [
        "https://img.example/main.jpg",
        "https://img.example/dawn.jpg",
    ]
    assert story["images"][1]["credit"] == "Dawn"
    # the primary link goes through the logging redirect; one card per outlet, no strays
    assert [(s["name"], s["primary"]) for s in story["sources"]] == [
        ("The Wire", True),
        ("Dawn", False),
    ]
    assert story["sources"][0]["url"] == f"/r/{item.id}"


async def test_stories_of_other_readers_are_hidden(api: AsyncClient, db: AsyncSession) -> None:
    other = await make_user(db, email="other@example.com")
    foreign, *_ = await seed_edition(db, other)
    await sign_in(api, db)
    assert (await api.get(f"/stories/{foreign.id}")).status_code == 404
    assert (await api.get("/stories/not-a-uuid")).status_code == 422
