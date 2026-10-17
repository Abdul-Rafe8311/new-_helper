"""The interests page API, and live learning from POST /events (FakeLLM is never needed: the
learner makes no model calls)."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_background_sessionmaker
from app.api.routers.events import events_limiter
from app.core.ratelimit import SlidingWindowLimiter
from app.db.session import get_session
from app.main import create_app
from app.models import Article, ProfileChange, User
from app.personalize.config import DEFAULT_LEARNING
from app.services.interests import entity_id
from tests.conftest import TEST_SETTINGS
from tests.editions_helpers import sessionmaker_for
from tests.factories import DEFAULT_PASSWORD, make_user
from tests.test_reader_api import event, seed_edition

pytestmark = pytest.mark.integration

PROFILE = {
    "onboarding_completed": True,
    "topics": {"cricket": 0.9, "ai": 0.5},
    "entities": {"people": ["Babar Azam", "Ada"], "teams": ["Karachi Kings"]},
    "learned_entities": {"people": ["Ada"], "teams": ["Karachi Kings"]},
    "blocked": {"topics": ["celebrity"], "keywords": [], "sources": []},
    "learn_state": {
        "onboarding_defaults": {"topics": {"cricket": 0.7, "f1": 0.4}},
        "less_like_counts": {"celebrity": 3},
    },
}


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


async def reader(api: AsyncClient, db: AsyncSession, **profile: object) -> User:
    user = await make_user(
        db, email="reader@example.com", timezone="UTC", profile={**PROFILE, **profile}
    )
    response = await api.post(
        "/auth/login", json={"email": "reader@example.com", "password": DEFAULT_PASSWORD}
    )
    assert response.status_code == 200
    return user


async def changes(db: AsyncSession, kind: str | None = None) -> list[ProfileChange]:
    query = select(ProfileChange).order_by(ProfileChange.created_at)
    if kind:
        query = query.where(ProfileChange.kind == kind)
    return list((await db.scalars(query)).all())


async def test_every_route_needs_a_session(api: AsyncClient) -> None:
    for method, path in [
        ("GET", "/me/interests"),
        ("PUT", "/me/interests/topics"),
        ("POST", "/me/interests/entities/x/pin"),
        ("DELETE", "/me/interests/entities/x"),
        ("POST", "/me/interests/blocked"),
        ("DELETE", "/me/interests/blocked/celebrity"),
        ("POST", "/me/interests/blocked-sources"),
        ("DELETE", "/me/interests/blocked-sources/Dawn"),
        ("POST", "/me/interests/reset"),
        ("GET", "/me/interests/timeline"),
    ]:
        assert (await api.request(method, path)).status_code == 401, (method, path)


async def test_get_interests_lists_topics_entities_and_blocked(
    api: AsyncClient, db: AsyncSession
) -> None:
    await reader(api, db)
    body = (await api.get("/me/interests")).json()
    assert [t["slug"] for t in body["topics"]] == ["cricket", "ai"]
    assert body["topics"][0]["label"] == "Cricket"
    assert {(e["kind"], e["name"], e["pinned"]) for e in body["entities"]} == {
        ("people", "Ada", False),
        ("teams", "Karachi Kings", False),
    }
    assert body["blocked"] == [{"topic": "celebrity", "label": "celebrity"}]
    assert body["is_new"] is False


async def test_a_new_reader_has_the_empty_state(api: AsyncClient, db: AsyncSession) -> None:
    await reader(
        api,
        db,
        learned_entities={},
        blocked={"topics": [], "keywords": [], "sources": []},
        learn_state={},
    )
    body = (await api.get("/me/interests")).json()
    assert body["is_new"] is True
    assert body["entities"] == []
    assert body["blocked"] == []
    assert (await api.get("/me/interests/timeline")).json() == {"days": []}


async def test_moving_a_slider_saves_it_and_logs_a_manual_edit(
    api: AsyncClient, db: AsyncSession
) -> None:
    await reader(api, db)
    response = await api.put("/me/interests/topics", json={"topics": {"ai": 0.8, "cricket": 0.9}})
    assert response.status_code == 200
    assert {t["slug"]: t["weight"] for t in response.json()["topics"]} == {
        "cricket": 0.9,
        "ai": 0.8,
    }
    [row] = await changes(db, "topic_manual")  # cricket did not move, so it is not logged
    assert (row.key, row.before, row.after, row.run) == ("ai", 0.5, 0.8, "manual")
    assert row.signals == [{"type": "manual_edit", "weight": DEFAULT_LEARNING.manual_edit_weight}]
    timeline = (await api.get("/me/interests/timeline")).json()
    assert timeline["days"][0]["entries"][0]["text"] == "You set Artificial Intelligence to 80%"


async def test_a_catalogue_topic_can_be_added_and_removed(
    api: AsyncClient, db: AsyncSession
) -> None:
    await reader(api, db)
    weight = (await api.get("/catalogue/topics")).json()["default_weight"]
    assert weight < 1

    added = (await api.put("/me/interests/topics", json={"topics": {"tennis": weight}})).json()
    assert {t["slug"]: t["weight"] for t in added["topics"]}["tennis"] == weight
    assert next(t["label"] for t in added["topics"] if t["slug"] == "tennis") == "Tennis"

    removed = (await api.put("/me/interests/topics", json={"topics": {"tennis": 0}})).json()
    assert {t["slug"]: t["weight"] for t in removed["topics"]}["tennis"] == 0

    first, second = await changes(db, "topic_manual")  # both are logged, and history is kept
    assert (first.key, first.before, first.after) == ("tennis", 0.0, weight)
    assert (second.key, second.before, second.after) == ("tennis", weight, 0.0)
    for row in (first, second):
        assert row.run == "manual"
        assert row.signals == [
            {"type": "manual_edit", "weight": DEFAULT_LEARNING.manual_edit_weight}
        ]
    entries = (await api.get("/me/interests/timeline")).json()["days"][0]["entries"]
    assert [e["text"] for e in entries] == ["You removed Tennis", "You added Tennis at 80%"]


async def test_a_source_can_be_switched_off_and_on(api: AsyncClient, db: AsyncSession) -> None:
    user = await reader(api, db)
    off = (await api.post("/me/interests/blocked-sources", json={"source": "Dawn"})).json()
    assert off["blocked_sources"] == ["Dawn"]
    assert user.profile.blocked["sources"] == ["Dawn"]  # the retriever reads this
    await api.post("/me/interests/blocked-sources", json={"source": "Dawn"})
    assert len(await changes(db, "source_blocked")) == 1
    bad = await api.post("/me/interests/blocked-sources", json={"source": "Nope Daily"})
    assert bad.status_code == 422

    on = (await api.delete("/me/interests/blocked-sources/Dawn")).json()
    assert on["blocked_sources"] == []
    again = await api.delete("/me/interests/blocked-sources/Dawn")
    assert again.status_code == 404
    entries = (await api.get("/me/interests/timeline")).json()["days"][0]["entries"]
    assert [e["text"] for e in entries] == ["You switched Dawn back on", "You switched off Dawn"]


async def test_slider_input_is_validated(api: AsyncClient, db: AsyncSession) -> None:
    await reader(api, db)
    bodies: list[dict[str, dict[str, float]]] = [
        {"topics": {"ai": 1.5}},
        {"topics": {"nope": 0.5}},
        {"topics": {}},
    ]
    for body in bodies:
        assert (await api.put("/me/interests/topics", json=body)).status_code == 422


async def test_pin_unpin_and_remove_a_learned_entity(api: AsyncClient, db: AsyncSession) -> None:
    user = await reader(api, db)
    ada = entity_id("people", "Ada")
    pinned = (await api.post(f"/me/interests/entities/{ada}/pin")).json()
    assert [e["pinned"] for e in pinned["entities"] if e["name"] == "Ada"] == [True]
    assert len(await changes(db, "entity_pinned")) == 1
    await api.post(f"/me/interests/entities/{ada}/pin")  # already pinned: no second log row
    assert len(await changes(db, "entity_pinned")) == 1

    unpinned = (await api.post(f"/me/interests/entities/{ada}/pin", json={"pinned": False})).json()
    assert not any(e["pinned"] for e in unpinned["entities"])

    after = (await api.delete(f"/me/interests/entities/{ada}")).json()
    assert [e["name"] for e in after["entities"]] == ["Karachi Kings"]
    assert user.profile.entities["people"] == ["Babar Azam"]  # the onboarding name stays
    gone = await api.delete(f"/me/interests/entities/{ada}")
    assert gone.status_code == 404
    assert (await api.post("/me/interests/entities/unknown/pin")).status_code == 404


async def test_a_pinned_entity_survives_a_reset_of_nothing_else(
    api: AsyncClient, db: AsyncSession
) -> None:
    user = await reader(api, db)
    ada = entity_id("people", "Ada")
    await api.post(f"/me/interests/entities/{ada}/pin")
    assert user.profile.learn_state["pinned_entities"] == [ada]


async def test_block_and_unblock_a_topic(api: AsyncClient, db: AsyncSession) -> None:
    user = await reader(api, db)
    body = (await api.post("/me/interests/blocked", json={"topic": "f1"})).json()
    assert [b["topic"] for b in body["blocked"]] == ["celebrity", "f1"]
    assert (await api.post("/me/interests/blocked", json={"topic": "nope"})).status_code == 422

    body = (await api.delete("/me/interests/blocked/celebrity")).json()
    assert [b["topic"] for b in body["blocked"]] == ["f1"]
    # the "less like this" tally goes too, or the learner would block it again on the next one
    assert "celebrity" not in user.profile.learn_state["less_like_counts"]
    not_blocked = await api.delete("/me/interests/blocked/celebrity")
    assert not_blocked.status_code == 404
    kinds = [c.kind for c in await changes(db)]
    assert kinds == ["topic_blocked", "topic_unblocked"]


async def test_reset_returns_to_onboarding_defaults_and_keeps_history(
    api: AsyncClient, db: AsyncSession
) -> None:
    user = await reader(api, db)
    await api.put("/me/interests/topics", json={"topics": {"ai": 0.8}})
    body = (await api.post("/me/interests/reset")).json()
    assert {t["slug"]: t["weight"] for t in body["topics"]} == {"cricket": 0.7, "f1": 0.4}
    assert body["entities"] == []
    assert user.profile.entities == {
        "people": ["Babar Azam"],
        "teams": [],
    }
    kinds = [c.kind for c in await changes(db)]
    assert kinds == ["topic_manual", "reset"]  # earlier history is still there
    [reset] = await changes(db, "reset")
    assert reset.before["entities"] == ["Ada", "Karachi Kings"]
    texts = (await api.get("/me/interests/timeline")).json()["days"][0]["entries"]
    assert texts[0]["text"] == "Reset to your onboarding choices"


async def test_reset_without_a_snapshot_rebuilds_from_the_saved_beats(
    api: AsyncClient, db: AsyncSession
) -> None:
    await reader(api, db, learn_state={}, onboarding_state={"beats": {"topics": ["f1", "ai"]}})
    body = (await api.post("/me/interests/reset")).json()
    assert {t["slug"] for t in body["topics"]} == {"f1", "ai"}


async def test_timeline_is_plain_language_grouped_by_day_and_limited_to_30_days(
    api: AsyncClient, db: AsyncSession
) -> None:
    from datetime import UTC, datetime, timedelta

    user = await reader(api, db)
    now = datetime.now(UTC)

    def row(kind: str, key: str | None, days_ago: float, **kw: object) -> ProfileChange:
        return ProfileChange(
            user_id=user.id,
            kind=kind,
            key=key,
            reason="x",
            signals=kw.pop("signals", []),
            delta=kw.pop("delta", None),
            created_at=now - timedelta(days=days_ago),
            run="nightly",
            **kw,
        )

    sig = [{"type": "open", "article_id": "a", "weight": 1.0}] * 4
    db.add_all(
        [
            row("topic_weight", "f1", 0.0, delta=0.1, signals=sig, before=0.4, after=0.5),
            row("entity_promoted", "Max Verstappen", 0.0),
            row("topic_weight", "ai", 2.0, delta=-0.1, signals=sig[:1]),
            row("topic_decay", None, 1.0),  # housekeeping: hidden
            row("interest_vector", None, 1.0),
            row("topic_weight", "world", 45.0, delta=0.1),  # too old
        ]
    )
    await db.flush()
    days = (await api.get("/me/interests/timeline")).json()["days"]
    assert len(days) == 2
    assert days[0]["date"] > days[1]["date"]
    assert sorted(e["text"] for e in days[0]["entries"]) == [
        "Raised Formula 1: 4 recent reads of Formula 1 stories",
        "Started following Max Verstappen: it kept showing up in stories you liked",
    ]
    assert days[1]["entries"][0]["text"].startswith(
        "Lowered Artificial Intelligence: 1 recent skip"
    )


async def test_other_readers_cannot_touch_my_interests(api: AsyncClient, db: AsyncSession) -> None:
    await reader(api, db)
    other = await make_user(db, email="other@example.com", profile=PROFILE)
    db.add(ProfileChange(user_id=other.id, kind="reset", reason="x", signals=[], run="manual"))
    await db.flush()
    assert (await api.get("/me/interests/timeline")).json() == {"days": []}


# live learning ------------------------------------------------------------------------------


async def test_a_save_teaches_the_paper_straight_away(api: AsyncClient, db: AsyncSession) -> None:
    user = await reader(api, db, topics={"ai": 0.2}, learned_entities={}, learn_state={})
    items = await seed_edition(db, user)
    article = await db.get(Article, items[0].article_id)
    assert article is not None
    article.topics = {"ai": 1.0}
    await db.flush()

    response = await api.post("/events", json={"events": [event(items[0], "save")]})
    assert response.json() == {"accepted": 1, "rejected": 0}

    rows = await changes(db, "topic_weight")
    assert [(r.key, r.run) for r in rows] == [("ai", "incremental")]
    assert user.profile.topics["ai"] > 0.2
    # the nightly run will not count the same save twice
    assert str(items[0].id) in user.profile.learn_state["settled_items"]


async def test_weak_events_do_not_trigger_the_learner(api: AsyncClient, db: AsyncSession) -> None:
    user = await reader(api, db, learn_state={})
    items = await seed_edition(db, user)
    await api.post(
        "/events", json={"events": [event(items[0], "skip"), event(items[1], "dwell", value=40)]}
    )
    assert await changes(db) == []


async def test_three_less_likes_block_the_topic(api: AsyncClient, db: AsyncSession) -> None:
    user = await reader(
        api,
        db,
        topics={"celebrity": 0.5},
        blocked={"topics": [], "keywords": [], "sources": []},
        learn_state={},
    )
    items = await seed_edition(db, user)
    for item in items:
        article = await db.get(Article, item.article_id)
        assert article is not None
        article.topics = {"celebrity": 1.0}
    await db.flush()
    for item in items:
        await api.post("/events", json={"events": [event(item, "less_like")]})
    body = (await api.get("/me/interests")).json()
    assert [b["topic"] for b in body["blocked"]] == ["celebrity"]
    assert len(await changes(db, "topic_blocked")) == 1
