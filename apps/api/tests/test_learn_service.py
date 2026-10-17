from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models import (
    Edition,
    EditionItem,
    EditionStatus,
    EventType,
    PipelineRun,
    ProfileChange,
    ReaderEvent,
    ReaderProfile,
    Slot,
    User,
)
from app.personalize import stage as learn_stage
from app.personalize.learn_service import (
    has_strong_signal,
    learn_after_events,
    learn_reader,
)
from app.personalize.profile import profile_view
from app.pipeline import STAGE_FNS
from tests.editions_helpers import sessionmaker_for
from tests.factories import make_article, make_source, make_user

NOW = datetime(2026, 10, 17, 22, 0, tzinfo=UTC)
DIM = 384
pytestmark = pytest.mark.integration


def vec(axis: int) -> list[float]:
    v = [0.0] * DIM
    v[axis] = 1.0
    return v


class Paper:
    """One edition for one reader, with helpers to record what they did."""

    def __init__(self, db: AsyncSession, user: User, edition: Edition) -> None:
        self.db, self.user, self.edition = db, user, edition
        self.items: dict[UUID, EditionItem] = {}

    async def add(self, article_id: UUID, slot: Slot = Slot.STANDARD) -> EditionItem:
        item = EditionItem(
            edition_id=self.edition.id,
            article_id=article_id,
            section="News",
            position=len(self.items),
            slot=slot,
        )
        self.db.add(item)
        await self.db.flush()
        self.items[article_id] = item
        return item

    async def event(
        self,
        article_id: UUID,
        kind: EventType,
        *,
        value: float | None = None,
        minutes: int = 60,
        **meta: Any,
    ) -> None:
        self.db.add(
            ReaderEvent(
                user_id=self.user.id,
                edition_id=self.edition.id,
                article_id=article_id,
                edition_item_id=self.items[article_id].id,
                type=kind,
                value=value,
                meta=meta,
                created_at=NOW - timedelta(minutes=minutes),
            )
        )
        await self.db.flush()


async def make_paper(db: AsyncSession, *, onboarded: bool = True, **profile: Any) -> Paper:
    user = await make_user(
        db,
        profile={
            "onboarding_completed": onboarded,
            "topics": {"ai": 0.5, "sports": 0.5},
            "interest_vector": vec(0),
            **profile,
        },
    )
    edition = Edition(
        user_id=user.id,
        edition_date=date(2026, 10, 17),
        number=1,
        status=EditionStatus.READY,
    )
    db.add(edition)
    await db.flush()
    return Paper(db, user, edition)


async def story(db: AsyncSession, topic: str, axis: int, source_id: UUID, **fields: Any) -> UUID:
    article = await make_article(
        db,
        topics={topic: 0.9},
        embedding=vec(axis),
        source_id=source_id,
        entities=fields.pop("entities", {}),
        **fields,
    )
    return article.id


async def profile_of(db: AsyncSession, user: User) -> ReaderProfile:
    row = (
        await db.execute(
            select(ReaderProfile)
            .where(ReaderProfile.user_id == user.id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    return row


async def changes_of(db: AsyncSession, user: User) -> list[ProfileChange]:
    rows = await db.execute(select(ProfileChange).where(ProfileChange.user_id == user.id))
    return list(rows.scalars())


async def test_nightly_run_learns_from_a_days_reading(db: AsyncSession) -> None:
    paper = await make_paper(db)
    source = await make_source(db)
    ada = {"people": ["Ada Lovelace"]}
    liked = [await story(db, "ai", 1, source.id, entities=ada) for _ in range(3)]
    ignored = await story(db, "sports", 2, source.id)
    for aid in [*liked, ignored]:
        await paper.add(aid)
        await paper.event(aid, EventType.IMPRESSION)
    for aid in liked:
        await paper.event(aid, EventType.OPEN)

    changes = await learn_reader(db, paper.user.id, now=NOW)
    profile = await profile_of(db, paper.user)

    assert profile.topics["ai"] > 0.5
    assert profile.topics["sports"] < 0.5
    assert profile.interest_vector is not None
    assert profile.interest_vector[1] > 0
    assert profile.entities["people"] == ["Ada Lovelace"]
    assert profile.learned_entities["people"] == ["Ada Lovelace"]
    assert profile.source_affinity[str(source.id)] > 0
    logged = await changes_of(db, paper.user)
    assert len(logged) == len(changes)
    assert {c.kind for c in logged} >= {
        "topic_weight",
        "interest_vector",
        "entity_promoted",
        "source_affinity",
    }
    assert {c.run for c in logged} == {"nightly"}
    topic_change = next(c for c in logged if c.kind == "topic_weight" and c.key == "ai")
    assert topic_change.before == 0.5
    assert topic_change.signals[0]["type"] == "open"
    assert topic_change.delta == pytest.approx(topic_change.after - topic_change.before, abs=1e-5)


async def test_events_are_consumed_once(db: AsyncSession) -> None:
    paper = await make_paper(db)
    source = await make_source(db)
    aid = await story(db, "ai", 1, source.id)
    await paper.add(aid)
    await paper.event(aid, EventType.OPEN)

    await learn_reader(db, paper.user.id, now=NOW)
    first = (await profile_of(db, paper.user)).topics["ai"]
    again = await learn_reader(db, paper.user.id, now=NOW + timedelta(hours=1))

    assert (await profile_of(db, paper.user)).topics["ai"] == pytest.approx(first, rel=0.01)
    assert {c.kind for c in again} <= {"topic_decay"}
    stats = (await profile_of(db, paper.user)).learn_state["source_stats"][str(source.id)]
    assert stats == {"pos": 1, "neg": 0}


async def test_repeated_less_like_blocks_the_topic(db: AsyncSession) -> None:
    paper = await make_paper(db)
    source = await make_source(db)
    for axis in range(3):
        aid = await story(db, "sports", axis + 1, source.id)
        await paper.add(aid)
        await paper.event(aid, EventType.LESS_LIKE, value=1)

    await learn_reader(db, paper.user.id, now=NOW)

    profile = await profile_of(db, paper.user)
    assert profile.blocked["topics"] == ["sports"]
    assert any(c.kind == "topic_blocked" for c in await changes_of(db, paper.user))


async def test_ignored_explore_picks_lower_the_explore_rate(db: AsyncSession) -> None:
    paper = await make_paper(db)
    source = await make_source(db)
    for axis in range(4):
        aid = await story(db, "culture", axis + 1, source.id)
        await paper.add(aid, Slot.EXPLORE)
        await paper.event(aid, EventType.IMPRESSION)

    await learn_reader(db, paper.user.id, now=NOW)

    assert (await profile_of(db, paper.user)).explore_rate == pytest.approx(0.15 * 0.8)


async def test_engaged_explore_topic_graduates(db: AsyncSession) -> None:
    paper = await make_paper(db)
    source = await make_source(db)
    aid = await story(db, "culture", 1, source.id)
    await paper.add(aid, Slot.EXPLORE)
    await paper.event(aid, EventType.OPEN)

    await learn_reader(db, paper.user.id, now=NOW)

    assert (await profile_of(db, paper.user)).topics["culture"] >= 0.4


async def test_incremental_run_learns_only_strong_signals_and_settles_them(
    db: AsyncSession,
) -> None:
    paper = await make_paper(db)
    source = await make_source(db)
    wanted = await story(db, "ai", 1, source.id)
    plain = await story(db, "sports", 2, source.id)
    for aid in (wanted, plain):
        await paper.add(aid)
    await paper.event(wanted, EventType.MORE_LIKE, value=1)
    await paper.event(plain, EventType.OPEN)

    changes = await learn_reader(db, paper.user.id, now=NOW, nightly=False)

    assert {c.run for c in await changes_of(db, paper.user)} == {"incremental"}
    assert not any(c.kind == "topic_decay" for c in changes)
    profile = await profile_of(db, paper.user)
    assert profile.topics["ai"] > 0.5
    assert profile.topics["sports"] == 0.5  # a plain open waits for the nightly run
    assert profile.learn_state["settled_items"] == [str(paper.items[wanted].id)]
    assert profile.learn_state.get("last_event_at") is None

    await learn_reader(db, paper.user.id, now=NOW + timedelta(hours=1))

    after = await profile_of(db, paper.user)
    stats = after.learn_state["source_stats"][str(source.id)]
    assert stats["pos"] == 2  # more_like once (incremental) + the open once (nightly)
    assert after.learn_state["settled_items"] == []


async def test_unonboarded_readers_are_left_alone(db: AsyncSession) -> None:
    paper = await make_paper(db, onboarded=False)
    assert await learn_reader(db, paper.user.id, now=NOW) == []
    assert await changes_of(db, paper.user) == []


async def test_a_reader_with_no_events_only_decays(db: AsyncSession) -> None:
    paper = await make_paper(db)
    changes = await learn_reader(db, paper.user.id, now=NOW)
    assert [c.kind for c in changes] == ["topic_decay"]


def test_only_strong_events_trigger_an_incremental_run() -> None:
    assert has_strong_signal(["impression", "save"])
    assert has_strong_signal(["more_like"])
    assert has_strong_signal(["less_like"])
    assert not has_strong_signal(["impression", "dwell", "skip", "open"])


async def test_learn_after_events_skips_weak_batches(db: AsyncSession) -> None:
    paper = await make_paper(db)
    sessionmaker = sessionmaker_for(db)
    assert await learn_after_events(sessionmaker, paper.user.id, ["impression", "dwell"]) == []
    assert await changes_of(db, paper.user) == []

    source = await make_source(db)
    aid = await story(db, "ai", 1, source.id)
    await paper.add(aid)
    await paper.event(aid, EventType.SAVE, value=1, minutes=1)
    changes = await learn_after_events(sessionmaker, paper.user.id, ["save"])
    assert any(c.kind == "topic_weight" for c in changes)


def test_learn_is_a_registered_pipeline_stage() -> None:
    assert "learn" in STAGE_FNS


async def test_learn_stage_covers_onboarded_readers_and_records_a_run(
    db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    onboarded = await make_paper(db)
    other = await make_paper(db, onboarded=False)
    monkeypatch.setattr(learn_stage, "get_sessionmaker", lambda: sessionmaker_for(db))

    await learn_stage.learn(Settings(env="test", jwt_secret="j" * 64, cron_secret="c" * 64))

    run = (
        (
            await db.execute(
                select(PipelineRun)
                .where(PipelineRun.stage == "learn")
                .order_by(PipelineRun.created_at.desc())
            )
        )
        .scalars()
        .first()
    )
    assert run is not None
    assert run.status.value == "succeeded"
    assert run.stats["readers"] >= 1
    assert run.stats["failed"] == 0
    assert (await changes_of(db, other.user)) == []
    assert await changes_of(db, onboarded.user)


async def test_profile_view_carries_what_was_learned(db: AsyncSession) -> None:
    paper = await make_paper(
        db,
        explore_rate=0.07,
        learned_entities={"people": ["Ada"]},
        entities={"people": ["Ada"], "companies": [], "teams": [], "places": []},
    )
    view = profile_view(paper.user, await profile_of(db, paper.user))
    assert view.explore_rate == 0.07
    assert view.learned_entities == {"people": ["Ada"]}
    assert "Ada" in view.terms
