"""Candidate retrieval: who could be in this reader's paper today.

Pool = cluster representatives from the last 24h that have a summary (the enrich stage only
summarises representatives), found by three arms that are unioned:
  vector     top 300 by cosine to the reader's interest_vector (pgvector)
  keyword    Postgres full-text match on the reader's keywords and entities
  big_story  the biggest multi-outlet clusters, which everybody should know about
Blocked topics/keywords/sources and anything shown in the last 7 editions are excluded.
"""

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enrich.clusters import ARTICLE_TIME
from app.models import Article, Edition, EditionItem, EventType, ReaderEvent, Source
from app.personalize.config import (
    RETRIEVAL_BIG_STORY_LIMIT,
    RETRIEVAL_BIG_STORY_MIN_SIZE,
    RETRIEVAL_KEYWORD_LIMIT,
    RETRIEVAL_VECTOR_LIMIT,
    RETRIEVAL_WINDOW_HOURS,
    SEEN_EDITIONS_LOOKBACK,
)
from app.personalize.types import Candidate, ProfileView

SEEN_EVENT_TYPES = (EventType.IMPRESSION, EventType.OPEN, EventType.SKIP)


async def shown_recently(
    session: AsyncSession, user_id: UUID, edition_date: date
) -> tuple[set[UUID], set[int]]:
    """Article ids and cluster ids printed in the reader's last 7 editions before this date."""
    rows = (
        await session.execute(
            select(EditionItem.article_id, Article.cluster_id)
            .join(Edition, Edition.id == EditionItem.edition_id)
            .join(Article, Article.id == EditionItem.article_id)
            .where(
                Edition.user_id == user_id,
                Edition.edition_date < edition_date,
                Edition.edition_date >= edition_date - timedelta(days=SEEN_EDITIONS_LOOKBACK),
            )
        )
    ).all()
    return {a for a, _ in rows}, {c for _, c in rows if c is not None}


async def previously_seen(session: AsyncSession, user_id: UUID) -> frozenset[UUID]:
    """Articles the reader has already had in front of them (impression, open or skip)."""
    ids = await session.scalars(
        select(ReaderEvent.article_id)
        .where(
            ReaderEvent.user_id == user_id,
            ReaderEvent.type.in_(SEEN_EVENT_TYPES),
            ReaderEvent.article_id.is_not(None),
        )
        .distinct()
    )
    return frozenset(i for i in ids if i is not None)


def _fts_query(terms: list[str]) -> str:
    return " or ".join('"' + t.replace('"', " ") + '"' for t in terms)


def _document() -> object:
    return func.to_tsvector(
        "english", func.concat_ws(" ", Article.title, Article.headline, Article.summary)
    )


def _pool(stmt: Select[Any], now: datetime, exclude: set[UUID], clusters: set[int]) -> Select[Any]:
    cutoff = now - timedelta(hours=RETRIEVAL_WINDOW_HOURS)
    stmt = stmt.where(Article.summary.is_not(None), cutoff <= ARTICLE_TIME, now >= ARTICLE_TIME)
    if exclude:
        stmt = stmt.where(Article.id.not_in(exclude))
    if clusters:
        stmt = stmt.where(or_(Article.cluster_id.is_(None), Article.cluster_id.not_in(clusters)))
    return stmt


async def retrieve_candidates(
    session: AsyncSession,
    profile: ProfileView,
    edition_date: date,
    *,
    now: datetime | None = None,
) -> list[Candidate]:
    now = now or datetime.now(UTC)
    seen_articles, seen_clusters = await shown_recently(session, profile.user_id, edition_date)

    def pool(stmt: Select[Any]) -> Select[Any]:
        return _pool(stmt, now, seen_articles, seen_clusters)

    origins: dict[UUID, set[str]] = defaultdict(set)

    if profile.interest_vector is not None:
        stmt = pool(select(Article.id).where(Article.embedding.is_not(None)))
        stmt = stmt.order_by(Article.embedding.cosine_distance(profile.interest_vector)).limit(
            RETRIEVAL_VECTOR_LIMIT
        )
        for article_id in await session.scalars(stmt):
            origins[article_id].add("vector")

    if terms := profile.terms:
        stmt = pool(select(Article.id)).where(
            _document().op("@@")(func.websearch_to_tsquery("english", _fts_query(terms)))  # type: ignore[attr-defined]
        )
        stmt = stmt.order_by(ARTICLE_TIME.desc()).limit(RETRIEVAL_KEYWORD_LIMIT)
        for article_id in await session.scalars(stmt):
            origins[article_id].add("keyword")

    stmt = pool(select(Article.id)).where(Article.cluster_size >= RETRIEVAL_BIG_STORY_MIN_SIZE)
    stmt = stmt.order_by(Article.cluster_size.desc(), ARTICLE_TIME.desc()).limit(
        RETRIEVAL_BIG_STORY_LIMIT
    )
    for article_id in await session.scalars(stmt):
        origins[article_id].add("big_story")

    if not origins:
        return []
    result = await session.execute(
        select(Article, Source.name, Source.quality)
        .outerjoin(Source, Source.id == Article.source_id)
        .where(Article.id.in_(origins))
    )
    return _build([(a, n, q) for a, n, q in result.all()], origins, profile)


def _blocked(article: Article, source_name: str, profile: ProfileView) -> bool:
    if profile.blocked_topics & set(article.topics):
        return True
    text = f"{article.title} {article.headline or ''} {article.summary or ''}".lower()
    if any(k.lower() in text for k in profile.blocked_keywords):
        return True
    blocked_sources = {s.lower() for s in profile.blocked_sources}
    return bool(blocked_sources & {source_name.lower(), str(article.source_id).lower()})


def _build(
    rows: list[tuple[Article, str | None, float | None]],
    origins: dict[UUID, set[str]],
    profile: ProfileView,
) -> list[Candidate]:
    out: list[Candidate] = []
    for article, source_name, quality in rows:
        name = source_name or "Unknown source"
        if _blocked(article, name, profile):
            continue
        out.append(
            Candidate(
                id=article.id,
                url=article.url,
                title=article.title,
                headline=article.headline or article.title,
                summary=article.summary or "",
                key_facts=tuple(str(f) for f in article.key_facts or []),
                source_id=article.source_id,
                source_name=name,
                source_quality=quality if quality is not None else 0.5,
                cluster_id=article.cluster_id,
                cluster_size=article.cluster_size or 1,
                topics=dict(article.topics or {}),
                entities={k: list(v) for k, v in (article.entities or {}).items()},
                embedding=list(article.embedding) if article.embedding is not None else None,
                published_at=article.published_at,
                image_url=article.image_url,
                origins=frozenset(origins[article.id]),
            )
        )
    out.sort(key=lambda c: str(c.id))  # stable order regardless of the database's row order
    return out
