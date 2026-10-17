"""Finish onboarding: build the profile and open the first edition."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.enrich.clusters import ARTICLE_TIME
from app.enrich.topics import load_prototypes
from app.models import Article, Depth, Edition, EditionStatus, User
from app.onboarding.generator import STAGES
from app.onboarding.profile_builder import (
    BuilderInput,
    TasteAnswer,
    build_profile,
    collect_keywords,
    weighted_mean,
)
from app.onboarding.service import taste_answers
from app.schemas.onboarding import BeatsStep, NameStep, ReadingStep, WordsStep

KEYWORD_WINDOW = timedelta(days=7)
ARTICLES_PER_KEYWORD = 5
STALE_AFTER = timedelta(seconds=90)  # a pending edition this old lost its worker (restart)


def default_paper_name(display_name: str) -> str:
    first = display_name.split()[0] if display_name.split() else "Reader"
    return f"The {first} Morning"


async def keyword_vectors(session: AsyncSession, keywords: list[str]) -> list[list[float]]:
    """Per keyword, the mean stored embedding of recent articles whose text matches it."""
    since = datetime.now(UTC) - KEYWORD_WINDOW
    document = func.to_tsvector("english", Article.title + " " + func.coalesce(Article.excerpt, ""))
    out: list[list[float]] = []
    for keyword in keywords[:12]:
        rows = await session.execute(
            select(Article.embedding)
            .where(
                document.bool_op("@@")(func.websearch_to_tsquery("english", keyword)),
                Article.embedding.is_not(None),
                since <= ARTICLE_TIME,
            )
            .order_by(ARTICLE_TIME.desc())
            .limit(ARTICLES_PER_KEYWORD)
        )
        vectors = [[float(x) for x in v] for (v,) in rows.all() if v is not None]
        if mean := weighted_mean([(1.0, v) for v in vectors]):
            out.append(mean)
    return out


async def _taste(session: AsyncSession, user_id: UUID) -> list[TasteAnswer]:
    answers = await taste_answers(session, user_id)
    if not answers:
        return []
    rows = await session.execute(
        select(Article.id, Article.topics, Article.embedding).where(Article.id.in_(answers))
    )
    return [
        TasteAnswer(
            topics,
            [float(x) for x in embedding] if embedding is not None else None,
            liked=answers[article_id],
        )
        for article_id, topics, embedding in rows.all()
    ]


async def build_and_store_profile(session: AsyncSession, user: User) -> None:
    profile = user.profile
    state = profile.onboarding_state or {}
    if state.get("beats") is None:
        raise AppError(409, "beats_missing", "Pick your topics before finishing")
    beats = BeatsStep.model_validate(state["beats"])
    words = WordsStep.model_validate(state["words"]) if state.get("words") else None
    name = NameStep.model_validate(state["name"]) if state.get("name") else None
    reading = ReadingStep.model_validate(state["reading"]) if state.get("reading") else None

    inp = BuilderInput(
        explicit_topics=beats.topics,
        deeper=beats.deeper,
        parsed=words.parsed if words else None,
        raw_text=words.text if words else "",
        taste=await _taste(session, user.id),
        prototypes=await load_prototypes(session),
    )
    inp = replace(inp, keyword_vectors=await keyword_vectors(session, collect_keywords(inp)))
    built = build_profile(inp)

    profile.topics = built.topics
    profile.keywords = built.keywords
    profile.entities = built.entities
    profile.blocked = built.blocked
    profile.context_notes = built.context_notes
    profile.interest_vector = built.interest_vector
    profile.paper_name = (name.paper_name if name else None) or default_paper_name(
        user.display_name
    )
    if reading is not None:
        profile.reading_minutes = reading.reading_minutes
        profile.depth = Depth(reading.depth)
        profile.surprise_me = reading.surprise_me
    profile.onboarding_completed = True


async def open_first_edition(session: AsyncSession, user: User) -> tuple[Edition, bool]:
    """Today's edition for the reader, and whether the generator should (re)run for it."""
    today = datetime.now(ZoneInfo(user.timezone)).date()
    edition = await session.scalar(
        select(Edition).where(Edition.user_id == user.id, Edition.edition_date == today)
    )
    if edition is None:
        count = await session.scalar(select(func.count()).where(Edition.user_id == user.id))
        edition = Edition(
            user_id=user.id,
            edition_date=today,
            number=(count or 0) + 1,
            status=EditionStatus.PENDING,
            title=user.profile.paper_name,
            stats={"stage": STAGES[0]},
        )
        session.add(edition)
        return edition, True
    if edition.status == EditionStatus.READY:
        return edition, False
    stale = datetime.now(UTC) - edition.updated_at > STALE_AFTER
    if edition.status == EditionStatus.FAILED or stale:
        edition.status = EditionStatus.PENDING
        edition.stats = {**edition.stats, "stage": STAGES[0]}
        return edition, True
    return edition, False


async def complete_onboarding(session: AsyncSession, user: User) -> tuple[Edition, bool]:
    await build_and_store_profile(session, user)
    edition, run = await open_first_edition(session, user)
    await session.commit()
    await session.refresh(edition)
    return edition, run
