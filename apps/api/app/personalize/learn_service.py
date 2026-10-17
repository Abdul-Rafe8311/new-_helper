"""Run the learner against the database: load events, apply `learn()`, store the result.

Two entry points share one code path:
  * `learn_reader(..., nightly=True)`   the `learn` pipeline stage, everything since the watermark;
  * `learn_reader(..., nightly=False)`  right after an event batch with a strong signal
    (more_like, less_like, save): only stories carrying such a signal, remembered as "settled"
    so the nightly run does not count them twice.

Retractions only cancel inside a run: undoing a skip after the run that counted it does not
reverse that run's effect (the next signals correct it).
"""

from collections.abc import Collection
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import (
    Article,
    EditionItem,
    EventType,
    ProfileChange,
    ReaderEvent,
    ReaderProfile,
    Slot,
)
from app.personalize.config import DEFAULT_LEARNING, DEFAULT_SELECTION, LearningConfig
from app.personalize.learn import Change, LearnerState, StoryFacts, learn
from app.personalize.signals import RawEvent, story_signals

log = structlog.get_logger(__name__)

LEARNING_EVENT_TYPES = frozenset(
    {
        "impression",
        "open",
        "mark_read",
        "dwell",
        "skip",
        "more_like",
        "less_like",
        "save",
        "quiz_answer",
        "onboarding_like",
        "onboarding_skip",
    }
)

# `mark_read` (Task 10) is only a database enum value once its migration has run; asking Postgres
# for a value its enum lacks is an error, so query the intersection with the model's enum.
QUERYABLE_EVENT_TYPES = [t for t in EventType if t.value in LEARNING_EVENT_TYPES]


def state_from_profile(profile: ReaderProfile) -> LearnerState:
    """Copy the learner's slice out of the ORM row (values are plain JSON, copied not shared)."""
    saved: dict[str, Any] = profile.learn_state or {}
    blocked: dict[str, Any] = profile.blocked or {}
    return LearnerState(
        topics={k: float(v) for k, v in (profile.topics or {}).items()},
        interest_vector=[float(x) for x in profile.interest_vector]
        if profile.interest_vector is not None
        else None,
        entities={k: list(v) for k, v in (profile.entities or {}).items()},
        learned_entities={k: list(v) for k, v in (profile.learned_entities or {}).items()},
        blocked_topics=list(blocked.get("topics", [])),
        source_affinity={k: float(v) for k, v in (profile.source_affinity or {}).items()},
        explore_rate=profile.explore_rate,
        entity_counts={k: int(v) for k, v in saved.get("entity_counts", {}).items()},
        less_like_counts={k: int(v) for k, v in saved.get("less_like_counts", {}).items()},
        source_stats={
            k: {"pos": int(v.get("pos", 0)), "neg": int(v.get("neg", 0))}
            for k, v in saved.get("source_stats", {}).items()
        },
    )


def apply_state(profile: ReaderProfile, state: LearnerState) -> None:
    profile.topics = {k: round(v, 6) for k, v in state.topics.items()}
    profile.interest_vector = state.interest_vector
    profile.entities = state.entities
    profile.learned_entities = state.learned_entities
    blocked = dict(profile.blocked or {})
    blocked["topics"] = state.blocked_topics
    profile.blocked = blocked
    profile.source_affinity = {k: round(v, 6) for k, v in state.source_affinity.items()}
    profile.explore_rate = state.explore_rate


def _learn_state_json(
    previous: dict[str, Any], state: LearnerState, *, watermark: datetime | None, settled: list[str]
) -> dict[str, Any]:
    return {
        **previous,
        "entity_counts": state.entity_counts,
        "less_like_counts": state.less_like_counts,
        "source_stats": state.source_stats,
        "last_event_at": watermark.isoformat() if watermark else previous.get("last_event_at"),
        "settled_items": settled,
    }


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


async def _load_events(
    session: AsyncSession, user_id: UUID, since: datetime
) -> list[tuple[ReaderEvent, Slot | None]]:
    rows = await session.execute(
        select(ReaderEvent, EditionItem.slot)
        .outerjoin(EditionItem, EditionItem.id == ReaderEvent.edition_item_id)
        .where(
            ReaderEvent.user_id == user_id,
            ReaderEvent.created_at > since,
            ReaderEvent.article_id.is_not(None),
            ReaderEvent.type.in_(QUERYABLE_EVENT_TYPES),
        )
        .order_by(ReaderEvent.created_at)
    )
    return [(e, slot) for e, slot in rows.all()]


def _facts(article: Article, explore: bool) -> StoryFacts:
    return StoryFacts(
        article_id=article.id,
        topics={k: float(v) for k, v in (article.topics or {}).items()},
        entities={k: list(v) for k, v in (article.entities or {}).items()},
        embedding=[float(x) for x in article.embedding] if article.embedding is not None else None,
        source_id=str(article.source_id) if article.source_id else None,
        explore=explore,
    )


async def learn_reader(
    session: AsyncSession,
    user_id: UUID,
    *,
    now: datetime | None = None,
    nightly: bool = True,
    cfg: LearningConfig = DEFAULT_LEARNING,
) -> list[Change]:
    """Learn from one reader's new events; commits. Returns the changes made."""
    now = now or datetime.now(UTC)
    profile = (
        await session.execute(select(ReaderProfile).where(ReaderProfile.user_id == user_id))
    ).scalar_one_or_none()
    if profile is None or not profile.onboarding_completed:
        return []

    saved: dict[str, Any] = dict(profile.learn_state or {})
    floor = now - timedelta(days=cfg.lookback_days)
    watermark = _parse_time(saved.get("last_event_at"))
    since = max(watermark, floor) if watermark else floor
    settled = [str(x) for x in saved.get("settled_items", [])]

    loaded = await _load_events(session, user_id, since)
    raw: list[RawEvent] = []
    explore_articles: set[UUID] = set()
    for e, slot in loaded:
        if e.article_id is None:
            continue
        item_key = str(e.edition_item_id) if e.edition_item_id else None
        if item_key in settled:
            continue
        raw.append(
            RawEvent(
                type=e.type.value,
                item_id=e.edition_item_id,
                article_id=e.article_id,
                created_at=e.created_at,
                value=e.value,
                meta=e.meta or {},
            )
        )
        if slot is Slot.EXPLORE:
            explore_articles.add(e.article_id)

    article_ids = {e.article_id for e in raw}
    articles = {
        a.id: a
        for a in (await session.execute(select(Article).where(Article.id.in_(article_ids))))
        .scalars()
        .all()
    }
    signals = story_signals(raw, now, {a.id: a.word_count for a in articles.values()}, cfg)
    if not nightly:
        signals = [s for s in signals if s.strong]
    pairs = [(s, _facts(articles[s.article_id], s.article_id in explore_articles)) for s in signals]

    state = state_from_profile(profile)
    new_state, changes = learn(
        state,
        pairs,
        cfg,
        nightly=nightly,
        base_explore_rate=DEFAULT_SELECTION.explore_share,
    )

    new_settled = settled
    new_mark = watermark
    if nightly:
        # Events up to now are consumed; settled items are older than that so they can be dropped.
        new_mark = max((e.created_at for e, _ in loaded), default=watermark or now)
        new_settled = []
    else:
        new_settled = [*settled, *(str(s.item_id) for s in signals if s.item_id)]
        new_settled = new_settled[-cfg.settled_memory :]

    apply_state(profile, new_state)
    profile.learn_state = _learn_state_json(
        saved, new_state, watermark=new_mark, settled=new_settled
    )
    run = "nightly" if nightly else "incremental"
    session.add_all(
        ProfileChange(
            user_id=user_id,
            kind=c.kind,
            key=c.key,
            before=c.before,
            after=c.after,
            delta=c.delta,
            reason=c.reason,
            signals=c.signals,
            run=run,
        )
        for c in changes
    )
    await session.commit()
    log.info("learned", user_id=str(user_id), run=run, stories=len(pairs), changes=len(changes))
    return changes


def has_strong_signal(event_types: Collection[str], cfg: LearningConfig = DEFAULT_LEARNING) -> bool:
    """True when a batch holds an event that should trigger an incremental run."""
    return any(t in cfg.strong_events for t in event_types)


async def learn_after_events(
    sessionmaker: async_sessionmaker[AsyncSession],
    user_id: UUID,
    event_types: Collection[str],
    *,
    cfg: LearningConfig = DEFAULT_LEARNING,
) -> list[Change]:
    """Incremental run for the events router to schedule (as a background task) after a batch."""
    if not has_strong_signal(event_types, cfg):
        return []
    async with sessionmaker() as session:
        return await learn_reader(session, user_id, nightly=False, cfg=cfg)
