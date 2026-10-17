"""Reading editions back out of the database for the API."""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import Article, Edition, EditionItem, EditionStatus, Source
from app.schemas.editions import EditionItemOut, EditionOut, EditionSummary

ARCHIVE_LIMIT = 90


async def get_edition_out(session: AsyncSession, user_id: uuid.UUID, day: date) -> EditionOut:
    edition = await session.scalar(
        select(Edition).where(Edition.user_id == user_id, Edition.edition_date == day)
    )
    if edition is None:
        raise AppError(404, "edition_not_found", f"No edition for {day.isoformat()}")
    return await to_out(session, edition)


async def to_out(session: AsyncSession, edition: Edition) -> EditionOut:
    rows = (
        await session.execute(
            select(EditionItem, Article, Source.name)
            .join(Article, Article.id == EditionItem.article_id)
            .outerjoin(Source, Source.id == Article.source_id)
            .where(EditionItem.edition_id == edition.id)
            .order_by(EditionItem.position)
        )
    ).all()
    items = [
        EditionItemOut(
            id=item.id,
            article_id=article.id,
            section=item.section,
            position=item.position,
            slot=item.slot,
            headline=item.headline or article.title,
            summary=item.summary or article.summary or "",
            why_text=item.why_text,
            url=article.url,
            source=source or "Unknown source",
            image_url=article.image_url,
            published_at=article.published_at,
            score=item.score,
            score_breakdown=item.score_breakdown,
        )
        for item, article, source in rows
    ]
    return EditionOut(
        id=edition.id,
        date=edition.edition_date,
        number=edition.number,
        status=edition.status,
        title=edition.title,
        editor_note=edition.editor_note,
        layout=edition.layout,
        items=items,
        stats=edition.stats,
        generated_at=edition.generated_at,
    )


async def list_archive(session: AsyncSession, user_id: uuid.UUID) -> list[EditionSummary]:
    editions = await session.scalars(
        select(Edition)
        .where(Edition.user_id == user_id, Edition.status == EditionStatus.READY)
        .order_by(Edition.edition_date.desc())
        .limit(ARCHIVE_LIMIT)
    )
    return [
        EditionSummary(
            id=e.id,
            date=e.edition_date,
            number=e.number,
            title=e.title,
            item_count=int(e.stats.get("items", 0)),
            top_topics=list(e.stats.get("top_topics", [])),
        )
        for e in editions
    ]
