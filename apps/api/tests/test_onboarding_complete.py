from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_edition_generator
from app.editions.service import EditionService
from app.models import Edition, EditionStatus, ReaderProfile, TopicPrototype, User
from app.onboarding.completion import default_paper_name
from app.onboarding.generator import STAGES, ComposerEditionGenerator
from tests.editions_helpers import fake_editor, seed_articles, sessionmaker_for
from tests.test_onboarding_api import (
    BEATS,
    NAME,
    READING,
    WORDS,
    login,
    put_step,
    seed_news,
)

pytestmark = pytest.mark.integration


class RecordingGenerator:
    def __init__(self) -> None:
        self.started: list[UUID] = []

    async def generate(self, edition_id: UUID) -> None:
        self.started.append(edition_id)


@pytest.fixture
def generator(api: FastAPI) -> RecordingGenerator:
    fake = RecordingGenerator()
    api.dependency_overrides[get_edition_generator] = lambda: fake
    return fake


def test_default_paper_name() -> None:
    assert default_paper_name("Abdul Rafe") == "The Abdul Morning"
    assert default_paper_name("  ") == "The Reader Morning"


async def test_complete_needs_topics(
    client: AsyncClient, db: AsyncSession, generator: RecordingGenerator
) -> None:
    await login(client, db)
    response = await client.post("/onboarding/complete")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "beats_missing"
    assert generator.started == []


async def test_complete_builds_the_profile_and_starts_the_edition(
    client: AsyncClient, db: AsyncSession, generator: RecordingGenerator
) -> None:
    await login(client, db)
    articles = await seed_news(db)
    db.add_all(
        TopicPrototype(slug=slug, description=slug, embedding=[1.0 if slug == "ai" else 0.0] * 384)
        for slug in ("ai", "cricket", "f1")
    )
    await put_step(client, 1, NAME)
    await put_step(client, 2, BEATS)
    await put_step(client, 3, WORDS)
    await put_step(client, 5, READING)
    deck = (await client.get("/onboarding/headlines")).json()["headlines"]
    for headline in deck[:4]:
        await client.post(
            "/onboarding/taste", json={"article_id": headline["id"], "interested": True}
        )
    assert articles

    response = await client.post("/onboarding/complete")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert generator.started == [UUID(body["edition_id"])]

    profile = (await client.get("/me/profile")).json()
    assert profile["onboarding_completed"] is True
    assert profile["paper_name"] == "The Rafe Morning"
    assert profile["reading_minutes"] == 10
    assert profile["depth"] == "deep"
    assert profile["surprise_me"] is False
    assert profile["topics"]["ai"] == 1.0
    assert 0 < profile["topics"]["cricket"] <= 1
    assert "film-tv" not in profile["topics"]
    assert profile["blocked"]["topics"] == ["film-tv"]
    assert {"AI agents", "PSL", "Test cricket"} <= set(profile["keywords"])
    assert profile["context_notes"] == "Runs an agency"

    stored = await db.scalar(
        select(ReaderProfile.interest_vector)
        .join(User, User.id == ReaderProfile.user_id)
        .where(User.email == "reader@example.com")
    )
    assert stored is not None
    assert len(stored) == 384

    state = (await client.get("/onboarding/state")).json()
    assert state["completed"] is True
    assert state["step"] == 6


async def test_complete_is_idempotent_while_pending(
    client: AsyncClient, db: AsyncSession, generator: RecordingGenerator
) -> None:
    await login(client, db)
    await put_step(client, 2, BEATS)
    first = (await client.post("/onboarding/complete")).json()
    second = (await client.post("/onboarding/complete")).json()
    assert first["edition_id"] == second["edition_id"]
    assert len(generator.started) == 1
    editions = (await db.execute(select(Edition))).scalars().all()
    assert len(editions) == 1
    assert editions[0].number == 1


async def test_complete_retries_a_failed_or_abandoned_edition(
    client: AsyncClient, db: AsyncSession, generator: RecordingGenerator
) -> None:
    await login(client, db)
    await put_step(client, 2, BEATS)
    edition_id = UUID((await client.post("/onboarding/complete")).json()["edition_id"])

    await db.execute(update(Edition).values(status=EditionStatus.FAILED))
    again = (await client.post("/onboarding/complete")).json()
    assert again == {"edition_id": str(edition_id), "status": "pending"}
    assert len(generator.started) == 2

    long_ago = datetime.now(UTC) - timedelta(minutes=10)
    await db.execute(update(Edition).values(updated_at=long_ago))
    await client.post("/onboarding/complete")
    assert len(generator.started) == 3


async def test_complete_leaves_a_ready_edition_alone(
    client: AsyncClient, db: AsyncSession, generator: RecordingGenerator
) -> None:
    await login(client, db)
    await put_step(client, 2, BEATS)
    await client.post("/onboarding/complete")
    await db.execute(update(Edition).values(status=EditionStatus.READY))
    response = (await client.post("/onboarding/complete")).json()
    assert response["status"] == "ready"
    assert len(generator.started) == 1


async def test_status_follows_the_edition(
    client: AsyncClient, db: AsyncSession, generator: RecordingGenerator
) -> None:
    await login(client, db)
    assert (await client.get("/onboarding/status")).json() == {
        "status": "none",
        "stage": None,
        "edition_id": None,
    }
    await put_step(client, 2, BEATS)
    edition_id = (await client.post("/onboarding/complete")).json()["edition_id"]
    pending = (await client.get("/onboarding/status")).json()
    assert pending == {"status": "pending", "stage": "gathering", "edition_id": edition_id}

    await db.execute(update(Edition).values(status=EditionStatus.READY, stats={"stage": "done"}))
    ready = (await client.get("/onboarding/status")).json()
    assert ready == {"status": "ready", "stage": "done", "edition_id": edition_id}


async def test_composer_generator_walks_the_stages_then_marks_ready(
    client: AsyncClient, db: AsyncSession, generator: RecordingGenerator
) -> None:
    await login(client, db)
    await put_step(client, 2, BEATS)
    edition_id = UUID((await client.post("/onboarding/complete")).json()["edition_id"])
    await seed_articles(db, "ai", "Agents", now=datetime.now(UTC))

    seen: list[str] = []
    original_commit = db.commit

    async def spy() -> None:
        await original_commit()
        edition = await db.get(Edition, edition_id)
        assert edition is not None
        seen.append(str(edition.stats.get("stage")))

    db.commit = spy  # type: ignore[method-assign]
    service = EditionService(sessionmaker_for(db), fake_editor(), "claude-sonnet-5-5")
    await ComposerEditionGenerator(service).generate(edition_id)
    db.commit = original_commit  # type: ignore[method-assign]

    assert [s for s in seen if s in STAGES][: len(STAGES)] == list(STAGES)
    edition = await db.get(Edition, edition_id)
    assert edition is not None
    assert edition.status == EditionStatus.READY
    assert edition.generated_at is not None
    assert edition.layout["composed_by"] == "llm"
    assert edition.stats["stage"] == "done"
    status = (await client.get("/onboarding/status")).json()
    assert status == {"status": "ready", "stage": "done", "edition_id": str(edition_id)}


async def test_composer_generator_marks_an_empty_day_as_failed(
    client: AsyncClient, db: AsyncSession, generator: RecordingGenerator
) -> None:
    await login(client, db)
    await put_step(client, 2, BEATS)
    edition_id = UUID((await client.post("/onboarding/complete")).json()["edition_id"])
    service = EditionService(sessionmaker_for(db), fake_editor(), "claude-sonnet-5-5")
    await ComposerEditionGenerator(service).generate(edition_id)
    edition = await db.get(Edition, edition_id)
    assert edition is not None
    assert edition.status == EditionStatus.FAILED
    assert "NoArticlesError" in edition.stats["error"]
