from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EventType, ReaderEvent
from tests.factories import DEFAULT_PASSWORD, make_article, make_source, make_user

pytestmark = pytest.mark.integration

NAME = {"paper_name": "The Rafe Morning", "city": "Lahore", "timezone": "Asia/Karachi"}
BEATS = {
    "topics": ["ai", "cricket", "f1"],
    "deeper": {"cricket": ["PSL", "Test cricket"]},
}
WORDS = {
    "text": "I follow AI agents and skip celebrity gossip",
    "parsed": {
        "topics": [{"slug": "ai", "weight": 0.9}],
        "keywords": ["AI agents"],
        "blocked": {"topics": ["film-tv"], "keywords": ["celebrity gossip"]},
        "context": "Runs an agency",
    },
}
READING = {"reading_minutes": 10, "depth": "deep", "surprise_me": False}
VECTOR = [0.1] * 384


async def login(client: AsyncClient, db: AsyncSession) -> None:
    await make_user(db, email="reader@example.com", display_name="Rafe Khan")
    response = await client.post(
        "/auth/login", json={"email": "reader@example.com", "password": DEFAULT_PASSWORD}
    )
    assert response.status_code == 200


async def put_step(client: AsyncClient, number: int, body: dict[str, Any]) -> Any:
    return await client.put(f"/onboarding/step/{number}", json=body)


async def test_everything_requires_a_session(client: AsyncClient) -> None:
    assert (await client.get("/onboarding/state")).status_code == 401
    assert (await client.put("/onboarding/step/1", json=NAME)).status_code == 401
    assert (await client.get("/onboarding/headlines")).status_code == 401
    body = {"article_id": "00000000-0000-0000-0000-000000000001", "interested": True}
    assert (await client.post("/onboarding/taste", json=body)).status_code == 401


async def test_fresh_state_starts_at_step_one(client: AsyncClient, db: AsyncSession) -> None:
    await login(client, db)
    state = (await client.get("/onboarding/state")).json()
    assert state["step"] == 1
    assert state["completed"] is False
    assert state["name"] is None
    assert state["answers"] == {}


async def test_steps_autosave_and_resume(client: AsyncClient, db: AsyncSession) -> None:
    await login(client, db)
    first = await put_step(client, 1, NAME)
    assert first.status_code == 200
    assert first.json()["step"] == 2

    await put_step(client, 2, BEATS)
    await put_step(client, 3, WORDS)
    final = (await put_step(client, 5, READING)).json()

    resumed = (await client.get("/onboarding/state")).json()
    assert resumed == final
    assert resumed["step"] == 6
    assert resumed["name"] == NAME
    assert resumed["beats"] == BEATS
    assert resumed["words"]["parsed"]["blocked"]["topics"] == ["film-tv"]
    assert resumed["reading"] == READING


async def test_going_back_does_not_lose_progress(client: AsyncClient, db: AsyncSession) -> None:
    await login(client, db)
    await put_step(client, 1, NAME)
    await put_step(client, 2, BEATS)
    state = (await put_step(client, 1, {**NAME, "paper_name": "The Other"})).json()
    assert state["step"] == 3
    assert state["name"]["paper_name"] == "The Other"
    assert state["beats"] == BEATS


async def test_name_step_updates_the_reader(client: AsyncClient, db: AsyncSession) -> None:
    await login(client, db)
    await put_step(client, 1, {**NAME, "timezone": "Europe/London", "city": "  London "})
    me = (await client.get("/auth/me")).json()
    assert me["timezone"] == "Europe/London"
    assert me["city"] == "London"


@pytest.mark.parametrize(
    ("number", "body"),
    [
        (1, {**NAME, "timezone": "Mars/Base"}),
        (1, {**NAME, "paper_name": "  "}),
        (2, {"topics": ["ai", "cricket"]}),
        (2, {"topics": ["ai", "cricket", "nope"]}),
        (2, {"topics": ["ai", "cricket", "f1"], "deeper": {"space": ["Mars"]}}),
        (3, {"text": "x" * 1501}),
        (3, {"text": "hi", "parsed": {"topics": [{"slug": "nope", "weight": 0.7}]}}),
        (5, {"reading_minutes": 7}),
        (5, {"reading_minutes": 10, "depth": "epic"}),
        (4, {"answered": -1}),
    ],
)
async def test_invalid_steps_are_rejected(
    client: AsyncClient, db: AsyncSession, number: int, body: dict[str, Any]
) -> None:
    await login(client, db)
    assert (await put_step(client, number, body)).status_code == 422
    assert (await client.get("/onboarding/state")).json()["step"] == 1


async def test_payload_must_match_the_step(client: AsyncClient, db: AsyncSession) -> None:
    await login(client, db)
    wrong = await put_step(client, 2, NAME)
    assert wrong.status_code == 422
    assert wrong.json()["error"]["code"] == "wrong_step_payload"
    assert (await put_step(client, 9, NAME)).status_code == 404
    assert (await put_step(client, 6, NAME)).status_code == 404


async def seed_news(db: AsyncSession) -> list[Any]:
    sources = [await make_source(db, name=f"Daily {n}", quality=0.5 + n / 20) for n in range(21)]
    topics = ["ai", "cricket", "f1", "space", "gaming", "books", "travel"]
    articles = []
    for i, topic in enumerate(topics):
        for j in range(3):
            articles.append(
                await make_article(
                    db,
                    title=f"Headline about {topic} number {j} for the morning",
                    source_id=sources[i * 3 + j].id,
                    topics={topic: 0.8},
                    embedding=VECTOR,
                    image_url="https://img.example/a.jpg",
                    published_at=datetime.now(UTC),
                    cluster_id=i * 10 + j,
                )
            )
    return articles


async def test_headlines_need_topics_first(client: AsyncClient, db: AsyncSession) -> None:
    await login(client, db)
    response = await client.get("/onboarding/headlines")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "beats_missing"


async def test_headlines_are_a_stable_diverse_deck(client: AsyncClient, db: AsyncSession) -> None:
    await login(client, db)
    await seed_news(db)
    await put_step(client, 2, BEATS)

    deck = (await client.get("/onboarding/headlines")).json()["headlines"]
    assert len(deck) == 12
    assert sum(h["outside"] for h in deck) == 3
    assert {"ai", "cricket", "f1"} <= {h["topic"] for h in deck}
    assert all(h["topic"] in BEATS["topics"] for h in deck if not h["outside"])
    assert deck[0]["source"].startswith("Daily ")
    assert deck[0]["image_url"] == "https://img.example/a.jpg"
    assert all(h["answer"] is None for h in deck)

    again = (await client.get("/onboarding/headlines")).json()["headlines"]
    assert [h["id"] for h in again] == [h["id"] for h in deck]  # a refresh keeps the deck


async def test_changing_topics_rebuilds_the_deck(client: AsyncClient, db: AsyncSession) -> None:
    await login(client, db)
    await seed_news(db)
    await put_step(client, 2, BEATS)
    first = (await client.get("/onboarding/headlines")).json()["headlines"]
    await put_step(client, 2, {"topics": ["space", "gaming", "books"]})
    second = (await client.get("/onboarding/headlines")).json()["headlines"]
    assert {h["topic"] for h in second if not h["outside"]} == {"space", "gaming", "books"}
    assert {h["id"] for h in first} != {h["id"] for h in second}


async def test_taste_answers_become_events_and_can_change(
    client: AsyncClient, db: AsyncSession
) -> None:
    await login(client, db)
    articles = await seed_news(db)
    await put_step(client, 2, BEATS)
    deck = (await client.get("/onboarding/headlines")).json()["headlines"]
    article_id = deck[0]["id"]

    like = await client.post(
        "/onboarding/taste", json={"article_id": article_id, "interested": True}
    )
    assert like.status_code == 204
    skip = await client.post(
        "/onboarding/taste", json={"article_id": deck[1]["id"], "interested": False}
    )
    assert skip.status_code == 204

    state = (await client.get("/onboarding/state")).json()
    assert state["answers"] == {article_id: True, deck[1]["id"]: False}
    shown = (await client.get("/onboarding/headlines")).json()["headlines"]
    assert [h["answer"] for h in shown[:2]] == [True, False]

    await client.post("/onboarding/taste", json={"article_id": article_id, "interested": False})
    events = (
        (
            await db.execute(
                select(ReaderEvent.type).where(ReaderEvent.article_id.in_([a.id for a in articles]))
            )
        )
        .scalars()
        .all()
    )
    assert sorted(events) == [EventType.ONBOARDING_SKIP, EventType.ONBOARDING_SKIP]
    assert (await client.get("/onboarding/state")).json()["answers"][article_id] is False


async def test_taste_answer_for_a_missing_story(client: AsyncClient, db: AsyncSession) -> None:
    await login(client, db)
    body = {"article_id": "00000000-0000-0000-0000-000000000001", "interested": True}
    response = await client.post("/onboarding/taste", json=body)
    assert response.status_code == 404
