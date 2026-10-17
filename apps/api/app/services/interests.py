"""What the paper has learned about a reader, and the reader's edits to it.

Edits are logged to `profile_changes` like the learner's own moves, with `run="manual"`, so the
timeline tells one story. Pins and the onboarding defaults live in `reader_profiles.learn_state`.
"""

import hashlib
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.catalogue import CATALOGUE
from app.core.errors import AppError
from app.models import ProfileChange, ReaderProfile, User
from app.onboarding.profile_builder import BuilderInput, topic_weights
from app.personalize.config import DEFAULT_LEARNING, LearningConfig
from app.schemas.interests import (
    BlockedTopic,
    InterestsOut,
    LearnedEntity,
    TimelineDay,
    TimelineEntry,
    TimelineOut,
    TopicWeight,
)

TIMELINE_DAYS = 30
TIMELINE_LIMIT = 400
LABELS = {t.slug: t.label for t in CATALOGUE}
# the learner's housekeeping rows say nothing a reader could use
HIDDEN_KINDS = frozenset({"topic_decay", "interest_vector", "source_affinity", "explore_rate"})


def label(slug: str) -> str:
    return LABELS.get(slug, slug)


def entity_id(kind: str, name: str) -> str:
    return hashlib.sha1(f"{kind}|{name}".encode()).hexdigest()[:12]  # noqa: S324 (not security)


def _pinned(profile: ReaderProfile) -> set[str]:
    return set((profile.learn_state or {}).get("pinned_entities", []))


def _set_learn_state(profile: ReaderProfile, **updates: Any) -> None:
    profile.learn_state = {**(profile.learn_state or {}), **updates}


def _log(
    profile: ReaderProfile,
    kind: str,
    key: str | None,
    before: Any,
    after: Any,
    reason: str,
    delta: float | None = None,
    weight: float | None = None,
) -> ProfileChange:
    signals = [{"type": "manual_edit", "weight": weight}] if weight is not None else []
    return ProfileChange(
        user_id=profile.user_id,
        kind=kind,
        key=key,
        before=before,
        after=after,
        delta=delta,
        reason=reason,
        signals=signals,
        run="manual",
        created_at=datetime.now(UTC),  # not the transaction's now(): order within one request
    )


def view(profile: ReaderProfile, has_history: bool) -> InterestsOut:
    pinned = _pinned(profile)
    entities = [
        LearnedEntity(id=entity_id(kind, n), kind=kind, name=n, pinned=entity_id(kind, n) in pinned)
        for kind, names in sorted((profile.learned_entities or {}).items())
        for n in names
    ]
    blocked = list((profile.blocked or {}).get("topics", []))
    topics = sorted((profile.topics or {}).items(), key=lambda kv: (-kv[1], kv[0]))
    return InterestsOut(
        topics=[TopicWeight(slug=s, label=label(s), weight=round(w, 4)) for s, w in topics],
        entities=entities,
        blocked=[BlockedTopic(topic=t, label=label(t)) for t in blocked],
        blocked_sources=list((profile.blocked or {}).get("sources", [])),
        is_new=not has_history and not entities and not blocked,
    )


async def has_history(session: AsyncSession, user_id: Any) -> bool:
    row = await session.scalar(
        select(ProfileChange.id).where(ProfileChange.user_id == user_id).limit(1)
    )
    return row is not None


async def get_interests(session: AsyncSession, profile: ReaderProfile) -> InterestsOut:
    return view(profile, await has_history(session, profile.user_id))


async def set_topics(
    session: AsyncSession,
    profile: ReaderProfile,
    weights: Mapping[str, float],
    cfg: LearningConfig = DEFAULT_LEARNING,
) -> InterestsOut:
    current = dict(profile.topics or {})
    changes: list[ProfileChange] = []
    for slug, weight in weights.items():
        before = float(current.get(slug, 0.0))
        after = round(weight, 4)
        if abs(after - before) < 1e-4:
            continue
        current[slug] = after
        changes.append(
            _log(
                profile,
                "topic_manual",
                slug,
                round(before, 4),
                after,
                "set by hand on the interests page",
                delta=round(after - before, 4),
                weight=cfg.manual_edit_weight,
            )
        )
    if changes:
        profile.topics = current
        session.add_all(changes)
        await session.commit()
    return await get_interests(session, profile)


def _find_entity(profile: ReaderProfile, ident: str) -> tuple[str, str]:
    for kind, names in (profile.learned_entities or {}).items():
        for name in names:
            if entity_id(kind, name) == ident:
                return kind, name
    raise AppError(404, "entity_not_found", "That item is not in your learned list")


async def pin_entity(
    session: AsyncSession, profile: ReaderProfile, ident: str, pinned: bool
) -> InterestsOut:
    _, name = _find_entity(profile, ident)
    current = _pinned(profile)
    if (ident in current) != pinned:
        _set_learn_state(
            profile, pinned_entities=sorted(current | {ident} if pinned else current - {ident})
        )
        session.add(
            _log(
                profile,
                "entity_pinned" if pinned else "entity_unpinned",
                name,
                not pinned,
                pinned,
                "kept for good" if pinned else "no longer kept for good",
            )
        )
        await session.commit()
    return await get_interests(session, profile)


async def remove_entity(session: AsyncSession, profile: ReaderProfile, ident: str) -> InterestsOut:
    kind, name = _find_entity(profile, ident)
    learned = {
        k: [n for n in v if not (k == kind and n == name)]
        for k, v in profile.learned_entities.items()
    }
    entities = {
        k: [n for n in v if not (k == kind and n == name)]
        for k, v in (profile.entities or {}).items()
    }
    profile.learned_entities = {k: v for k, v in learned.items() if v}
    profile.entities = entities
    state = profile.learn_state or {}
    counts = {k: v for k, v in state.get("entity_counts", {}).items() if k != f"{kind}|{name}"}
    _set_learn_state(
        profile,
        entity_counts=counts,
        pinned_entities=sorted(_pinned(profile) - {ident}),
    )
    session.add(_log(profile, "entity_removed", name, kind, None, "removed by hand"))
    await session.commit()
    return await get_interests(session, profile)


async def block_topic(session: AsyncSession, profile: ReaderProfile, topic: str) -> InterestsOut:
    blocked = dict(profile.blocked or {})
    topics = list(blocked.get("topics", []))
    if topic not in topics:
        blocked["topics"] = [*topics, topic]
        profile.blocked = blocked
        session.add(_log(profile, "topic_blocked", topic, False, True, "blocked by hand"))
        await session.commit()
    return await get_interests(session, profile)


async def unblock_topic(session: AsyncSession, profile: ReaderProfile, topic: str) -> InterestsOut:
    blocked = dict(profile.blocked or {})
    topics = list(blocked.get("topics", []))
    if topic not in topics:
        raise AppError(404, "topic_not_blocked", "That topic is not blocked")
    blocked["topics"] = [t for t in topics if t != topic]
    profile.blocked = blocked
    # forget the "less like this" tally, or the learner would block it again on the next one
    counts = {
        k: v
        for k, v in (profile.learn_state or {}).get("less_like_counts", {}).items()
        if k != topic
    }
    _set_learn_state(profile, less_like_counts=counts)
    session.add(_log(profile, "topic_unblocked", topic, True, False, "unblocked by hand"))
    await session.commit()
    return await get_interests(session, profile)


async def block_source(session: AsyncSession, profile: ReaderProfile, source: str) -> InterestsOut:
    blocked = dict(profile.blocked or {})
    sources = list(blocked.get("sources", []))
    if source not in sources:
        blocked["sources"] = [*sources, source]
        profile.blocked = blocked
        session.add(_log(profile, "source_blocked", source, False, True, "switched off by hand"))
        await session.commit()
    return await get_interests(session, profile)


async def unblock_source(
    session: AsyncSession, profile: ReaderProfile, source: str
) -> InterestsOut:
    blocked = dict(profile.blocked or {})
    sources = list(blocked.get("sources", []))
    if source not in sources:
        raise AppError(404, "source_not_blocked", "That source is not switched off")
    blocked["sources"] = [s for s in sources if s != source]
    profile.blocked = blocked
    session.add(_log(profile, "source_unblocked", source, True, False, "switched on by hand"))
    await session.commit()
    return await get_interests(session, profile)


def onboarding_defaults(profile: ReaderProfile) -> dict[str, float]:
    """Topic weights as onboarding set them: the snapshot, else rebuilt from the saved answers."""
    saved = (profile.learn_state or {}).get("onboarding_defaults")
    if isinstance(saved, dict) and isinstance(saved.get("topics"), dict):
        return {k: float(v) for k, v in saved["topics"].items()}
    beats = (profile.onboarding_state or {}).get("beats") or {}
    return topic_weights(BuilderInput(explicit_topics=list(beats.get("topics", []))))


async def reset_interests(session: AsyncSession, profile: ReaderProfile) -> InterestsOut:
    """Forget what was learned; the log keeps its history and gains a row saying so."""
    before_topics = dict(profile.topics or {})
    defaults = onboarding_defaults(profile)
    cleared = sorted(n for names in (profile.learned_entities or {}).values() for n in names)
    learned = profile.learned_entities or {}
    profile.entities = {
        k: [n for n in v if n not in set(learned.get(k, []))]
        for k, v in (profile.entities or {}).items()
    }
    profile.learned_entities = {}
    profile.topics = defaults
    _set_learn_state(profile, entity_counts={}, pinned_entities=[])
    session.add(
        _log(
            profile,
            "reset",
            None,
            {"topics": before_topics, "entities": cleared},
            {"topics": defaults},
            f"reset to your onboarding choices; forgot {len(cleared)} learned names",
        )
    )
    await session.commit()
    return await get_interests(session, profile)


# timeline ------------------------------------------------------------------------------------


def describe(c: ProfileChange) -> str | None:
    key = c.key or ""
    topic = label(key)
    if c.kind == "topic_weight":
        rose = (c.delta or 0) > 0
        n = len(c.signals or [])
        evidence = f"you {'engaged with' if rose else 'passed on'} {topic} stories"
        if n:
            evidence = f"{n} recent {'reads' if rose else 'skips'} of {topic} stories"
        return f"{'Raised' if rose else 'Lowered'} {topic}: {evidence}"
    if c.kind == "topic_manual":
        before, after = float(c.before or 0), float(c.after or 0)
        if before <= 0 < after:
            return f"You added {topic} at {round(after * 100)}%"
        if after <= 0 < before:
            return f"You removed {topic}"
        return f"You set {topic} to {round(after * 100)}%"
    if c.kind == "source_blocked":
        return f"You switched off {key}"
    if c.kind == "source_unblocked":
        return f"You switched {key} back on"
    if c.kind == "entity_promoted":
        return f"Started following {key}: it kept showing up in stories you liked"
    if c.kind == "entity_removed":
        return f"You removed {key} from what the paper follows"
    if c.kind == "entity_pinned":
        return f"You pinned {key}: it stays"
    if c.kind == "entity_unpinned":
        return f"You unpinned {key}"
    if c.kind == "topic_blocked":
        manual = c.run == "manual"
        return f"Blocked {topic}: " + (
            "you asked for it" if manual else "you kept asking for less of it"
        )
    if c.kind == "topic_unblocked":
        return f"Unblocked {topic}: you can see it again"
    if c.kind == "explore_graduated":
        return f"Added {topic} to your topics: you read a surprise pick"
    if c.kind == "reset":
        return "Reset to your onboarding choices"
    return None


async def timeline(session: AsyncSession, user: User, now: datetime | None = None) -> TimelineOut:
    now = now or datetime.now(UTC)
    rows = (
        (
            await session.execute(
                select(ProfileChange)
                .where(
                    ProfileChange.user_id == user.id,
                    ProfileChange.created_at >= now - timedelta(days=TIMELINE_DAYS),
                    ProfileChange.kind.not_in(HIDDEN_KINDS | {"topic_decay"}),
                )
                .order_by(ProfileChange.created_at.desc())
                .limit(TIMELINE_LIMIT)
            )
        )
        .scalars()
        .all()
    )
    tz = ZoneInfo(user.timezone)
    days: dict[str, list[TimelineEntry]] = {}
    for c in rows:
        text = describe(c)
        if text is None:
            continue
        local = c.created_at.astimezone(tz)
        days.setdefault(local.date().isoformat(), []).append(
            TimelineEntry(id=str(c.id), at=c.created_at.isoformat(), kind=c.kind, text=text)
        )
    return TimelineOut(days=[TimelineDay(date=d, entries=e) for d, e in days.items()])
