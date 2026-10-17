"""Onboarding state: autosaved steps, the taste test and its answers."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import Article, EventType, ReaderEvent, Source, User
from app.onboarding.headlines import load_candidates, pick_headlines
from app.schemas.onboarding import (
    BeatsStep,
    HeadlineOut,
    HeadlinesOut,
    NameStep,
    OnboardingStateOut,
    ReadingStep,
    StepIn,
    TasteStep,
    WordsStep,
)

FINALE_STEP = 6
_MODEL_FOR_STEP: dict[int, type[BaseModel]] = {
    1: NameStep,
    2: BeatsStep,
    3: WordsStep,
    4: TasteStep,
    5: ReadingStep,
}
_KEY_FOR_STEP = {1: "name", 2: "beats", 3: "words", 4: "taste_progress", 5: "reading"}
_TASTE_EVENTS = (EventType.ONBOARDING_LIKE, EventType.ONBOARDING_SKIP)


async def taste_answers(session: AsyncSession, user_id: UUID) -> dict[UUID, bool]:
    """Latest answer per article from the onboarding events (true = interested)."""
    rows = await session.execute(
        select(ReaderEvent.article_id, ReaderEvent.type)
        .where(ReaderEvent.user_id == user_id, ReaderEvent.type.in_(_TASTE_EVENTS))
        .order_by(ReaderEvent.created_at)
    )
    return {aid: kind == EventType.ONBOARDING_LIKE for aid, kind in rows.all() if aid is not None}


def _saved[M: BaseModel](state: dict[str, Any], key: str, model: type[M]) -> M | None:
    raw = state.get(key)
    return model.model_validate(raw) if raw is not None else None


async def get_state(session: AsyncSession, user: User) -> OnboardingStateOut:
    profile = user.profile
    state = profile.onboarding_state or {}
    return OnboardingStateOut(
        step=FINALE_STEP if profile.onboarding_completed else int(state.get("step", 1)),
        completed=profile.onboarding_completed,
        name=_saved(state, "name", NameStep),
        beats=_saved(state, "beats", BeatsStep),
        words=_saved(state, "words", WordsStep),
        reading=_saved(state, "reading", ReadingStep),
        answers=await taste_answers(session, user.id),
    )


async def save_step(
    session: AsyncSession, user: User, number: int, payload: StepIn
) -> OnboardingStateOut:
    expected = _MODEL_FOR_STEP.get(number)
    if expected is None:
        raise AppError(404, "unknown_step", f"There is no step {number}")
    if not isinstance(payload, expected):
        raise AppError(422, "wrong_step_payload", f"Step {number} expects a {expected.__name__}")

    profile = user.profile
    state = dict(profile.onboarding_state or {})
    state[_KEY_FOR_STEP[number]] = payload.model_dump(mode="json")
    state["step"] = min(FINALE_STEP, max(int(state.get("step", 1)), number + 1))
    if isinstance(payload, NameStep):
        user.city = payload.city or None
        user.timezone = payload.timezone
    if isinstance(payload, BeatsStep):
        # a different set of topics makes the stored taste-test deck stale
        state.pop("taste", None)
    profile.onboarding_state = state
    await session.commit()
    return await get_state(session, user)


async def get_headlines(session: AsyncSession, user: User) -> HeadlinesOut:
    profile = user.profile
    state = dict(profile.onboarding_state or {})
    beats = _saved(state, "beats", BeatsStep)
    if beats is None:
        raise AppError(409, "beats_missing", "Pick your topics before the taste test")

    deck = state.get("taste")
    if deck is None:
        picks = pick_headlines(await load_candidates(session), beats.topics)
        deck = {
            "ids": [str(p.candidate.id) for p in picks],
            "outside": [str(p.candidate.id) for p in picks if p.outside],
        }
        state["taste"] = deck
        profile.onboarding_state = state
        await session.commit()

    ids = [UUID(i) for i in deck["ids"]]
    articles = await _articles_by_id(session, ids)
    answers = await taste_answers(session, user.id)
    outside = set(deck["outside"])
    return HeadlinesOut(
        headlines=[
            HeadlineOut(
                id=i,
                headline=articles[i].headline,
                source=articles[i].source,
                image_url=articles[i].image_url,
                topic=articles[i].topic,
                outside=str(i) in outside,
                answer=answers.get(i),
            )
            for i in ids
            if i in articles
        ]
    )


@dataclass(frozen=True, slots=True)
class _DeckArticle:
    headline: str
    source: str
    image_url: str | None
    topic: str | None


async def _articles_by_id(session: AsyncSession, ids: list[UUID]) -> dict[UUID, _DeckArticle]:
    rows = await session.execute(
        select(Article, Source.name)
        .join(Source, Article.source_id == Source.id, isouter=True)
        .where(Article.id.in_(ids))
    )
    return {
        a.id: _DeckArticle(
            (a.headline or a.title).strip(),
            name or "Unknown source",
            a.image_url,
            max(a.topics, key=lambda t: a.topics[t]) if a.topics else None,
        )
        for a, name in rows.all()
    }


async def record_answer(
    session: AsyncSession, user: User, article_id: UUID, interested: bool
) -> None:
    """One onboarding event per article: answering again replaces the earlier answer."""
    if await session.get(Article, article_id) is None:
        raise AppError(404, "article_not_found", "That story is no longer available")
    await session.execute(
        delete(ReaderEvent).where(
            ReaderEvent.user_id == user.id,
            ReaderEvent.article_id == article_id,
            ReaderEvent.type.in_(_TASTE_EVENTS),
        )
    )
    session.add(
        ReaderEvent(
            user_id=user.id,
            article_id=article_id,
            type=EventType.ONBOARDING_LIKE if interested else EventType.ONBOARDING_SKIP,
            value=1.0 if interested else -1.0,
        )
    )
    await session.commit()
