"""The recall quiz: which days the reader finished it, and the streak that makes."""

import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Edition, EditionStatus, EventType, ReaderEvent
from app.schemas.quiz import QuizStreakOut

# Longest streak we look back for; keeps the events scan bounded.
LOOKBACK_DAYS = 400
# `meta.kind` of an answer to one of the edition's own questions; "Still remember?" answers carry
# "recall" and never count towards finishing a day.
QUIZ_KIND = "quiz"


def streak_from_days(finished: set[date], today: date) -> int:
    """Consecutive finished days ending today, or yesterday while today is still open.

    A day with no finished quiz in between resets it to zero.
    """
    day = today if today in finished else today - timedelta(days=1)
    count = 0
    while day in finished:
        count += 1
        day -= timedelta(days=1)
    return count


def _questions_in(layout: dict[str, object]) -> int:
    quiz = layout.get("quiz")
    return len(quiz) if isinstance(quiz, list) else 0


async def finished_days(session: AsyncSession, user_id: uuid.UUID, today: date) -> set[date]:
    """Days whose edition had a quiz and had every one of its questions answered."""
    rows = await session.execute(
        select(Edition.edition_date, Edition.layout, ReaderEvent.meta)
        .join(ReaderEvent, ReaderEvent.edition_id == Edition.id)
        .where(
            Edition.user_id == user_id,
            Edition.status == EditionStatus.READY,
            Edition.edition_date >= today - timedelta(days=LOOKBACK_DAYS),
            ReaderEvent.user_id == user_id,
            ReaderEvent.type == EventType.QUIZ_ANSWER,
        )
    )
    answered: dict[date, set[object]] = {}
    needed: dict[date, int] = {}
    for day, layout, meta in rows:
        if meta.get("kind", QUIZ_KIND) != QUIZ_KIND:
            continue
        needed[day] = _questions_in(layout)
        answered.setdefault(day, set()).add(meta.get("q"))
    return {day for day, qs in answered.items() if needed[day] and len(qs) >= needed[day]}


async def quiz_streak(session: AsyncSession, user_id: uuid.UUID, today: date) -> QuizStreakOut:
    finished = await finished_days(session, user_id, today)
    return QuizStreakOut(streak=streak_from_days(finished, today), done_today=today in finished)
