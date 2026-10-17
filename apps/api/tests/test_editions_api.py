from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import FakeLLM
from app.api.deps import get_edition_service
from app.db.session import get_session
from app.editions.service import MAX_REGENERATIONS_PER_DAY, EditionService, local_date
from app.main import create_app
from app.models import Edition, EditionStatus, User
from tests.conftest import TEST_SETTINGS
from tests.editions_helpers import E, fake_editor, seed_articles, sessionmaker_for
from tests.factories import DEFAULT_PASSWORD, make_user

pytestmark = pytest.mark.integration

MODEL = "claude-sonnet-5-5"


@pytest.fixture
def llm() -> FakeLLM:
    return fake_editor()


@pytest.fixture
async def api(db: AsyncSession, llm: FakeLLM) -> AsyncIterator[AsyncClient]:
    """An app whose edition service uses a FakeLLM and the test's transaction."""
    app = create_app(TEST_SETTINGS)

    async def _session() -> AsyncIterator[AsyncSession]:
        yield db

    service = EditionService(sessionmaker_for(db), llm, MODEL)
    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_edition_service] = lambda: service
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def login(client: AsyncClient, db: AsyncSession, email: str = "reader@example.com") -> None:
    await make_user(
        db,
        email=email,
        display_name="Sara Khan",
        timezone="UTC",
        profile={"topics": {"ai": 0.9}, "interest_vector": E.embed(["Agents story 0"])[0]},
    )
    response = await client.post("/auth/login", json={"email": email, "password": DEFAULT_PASSWORD})
    assert response.status_code == 200


def today() -> date:
    return local_date("UTC", datetime.now(UTC))


async def test_every_edition_route_needs_a_session(api: AsyncClient) -> None:
    for method, path in (
        ("GET", "/editions"),
        ("GET", "/editions/today"),
        ("GET", "/editions/2026-10-17"),
        ("POST", "/editions/today/regenerate"),
    ):
        assert (await api.request(method, path)).status_code == 401, path


async def test_today_is_404_before_anything_is_built(api: AsyncClient, db: AsyncSession) -> None:
    await login(api, db)
    response = await api.get("/editions/today")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "edition_not_found"
    assert (await api.get("/editions")).json() == []
    assert (await api.get("/editions/not-a-date")).status_code == 422


async def test_regenerate_builds_in_the_background_then_today_serves_it(
    api: AsyncClient, db: AsyncSession
) -> None:
    await seed_articles(db, "ai", "Agents", now=datetime.now(UTC))
    await login(api, db)
    started = await api.post("/editions/today/regenerate")
    assert started.status_code == 202
    assert started.json()["status"] == "pending"
    assert started.json()["items"] == []

    edition = (await api.get("/editions/today")).json()
    assert edition["status"] == "ready"
    assert edition["date"] == today().isoformat()
    assert edition["number"] == 1
    assert edition["title"] == "The Fake Morning"
    assert edition["layout"]["tagline"] == "Composed by a fake editor"
    items = edition["items"]
    assert [i["position"] for i in items] == list(range(len(items)))
    assert items
    first = items[0]
    assert {"headline", "summary", "why_text", "url", "source", "section", "slot"} <= set(first)
    assert first["url"].startswith("https://example.com/")
    assert first["why_text"]
    assert {i["id"] for i in items} == {
        i for s in edition["layout"]["sections"] for i in s["item_ids"]
    }

    by_date = await api.get(f"/editions/{today().isoformat()}")
    assert by_date.json()["id"] == edition["id"]
    assert (await api.get("/editions/2020-01-01")).status_code == 404


async def test_archive_lists_ready_editions_newest_first(
    api: AsyncClient, db: AsyncSession
) -> None:
    await seed_articles(db, "ai", "Agents", now=datetime.now(UTC))
    await login(api, db)
    await api.post("/editions/today/regenerate")
    user_edition = (await api.get("/editions/today")).json()
    older = Edition(
        user_id=await _user_id(db),
        edition_date=today() - timedelta(days=1),
        number=0,
        status=EditionStatus.READY,
        title="Yesterday",
        stats={"items": 9, "top_topics": ["AI", "Cricket"]},
    )
    failed = Edition(
        user_id=older.user_id,
        edition_date=today() - timedelta(days=2),
        number=0,
        status=EditionStatus.FAILED,
    )
    db.add_all([older, failed])
    await db.flush()
    archive = (await api.get("/editions")).json()
    assert [e["date"] for e in archive] == [
        today().isoformat(),
        (today() - timedelta(days=1)).isoformat(),
    ]
    assert archive[0]["id"] == user_edition["id"]
    assert archive[0]["item_count"] == len(user_edition["items"])
    assert archive[1] == {
        "id": str(older.id),
        "date": older.edition_date.isoformat(),
        "number": 0,
        "title": "Yesterday",
        "item_count": 9,
        "top_topics": ["AI", "Cricket"],
    }


async def _user_id(db: AsyncSession) -> UUID:
    user_id = await db.scalar(select(User.id).where(User.email == "reader@example.com"))
    assert user_id is not None
    return user_id


async def test_regeneration_is_limited_to_three_a_day(api: AsyncClient, db: AsyncSession) -> None:
    await seed_articles(db, "ai", "Agents", now=datetime.now(UTC))
    await login(api, db)
    assert (await api.post("/editions/today/regenerate")).status_code == 202  # the first build
    for _ in range(MAX_REGENERATIONS_PER_DAY):
        assert (await api.post("/editions/today/regenerate")).status_code == 202
    blocked = await api.post("/editions/today/regenerate")
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "regeneration_limit"
    assert (await api.get("/editions/today")).json()["stats"]["regenerations"] == 3


async def test_a_paper_already_being_built_is_not_started_twice(
    api: AsyncClient, db: AsyncSession, llm: FakeLLM
) -> None:
    await login(api, db)
    db.add(
        Edition(
            user_id=await _user_id(db),
            edition_date=today(),
            number=1,
            status=EditionStatus.PENDING,
        )
    )
    await db.flush()
    response = await api.post("/editions/today/regenerate")
    assert response.status_code == 202
    assert response.json()["status"] == "pending"
    assert llm.calls == []


async def test_readers_cannot_see_each_others_papers(api: AsyncClient, db: AsyncSession) -> None:
    await seed_articles(db, "ai", "Agents", now=datetime.now(UTC))
    await login(api, db, "first@example.com")
    await api.post("/editions/today/regenerate")
    assert (await api.get("/editions/today")).status_code == 200
    await api.post("/auth/logout")
    await login(api, db, "second@example.com")
    assert (await api.get("/editions/today")).status_code == 404
    assert (await api.get("/editions")).json() == []
