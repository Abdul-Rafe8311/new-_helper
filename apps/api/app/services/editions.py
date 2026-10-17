"""Reading editions back out of the database for the API."""

import uuid
from collections.abc import Sequence
from datetime import date, timedelta
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import Article, Edition, EditionItem, EditionStatus, EventType, ReaderEvent, Source
from app.pdf.snapshot import fact_texts
from app.schemas.editions import EditionItemOut, EditionOut, EditionSummary, ItemState, SavedItem
from app.schemas.stories import StoryImage, StoryOut, StorySource

ARCHIVE_PAGE = 20
ARCHIVE_MAX_PAGE = 60
TOP_TOPICS = 3

# Events that decide how a story looks to its reader. ``value == 0`` retracts a toggle.
_STATE_EVENTS = (
    EventType.OPEN,
    EventType.MARK_READ,
    EventType.SKIP,
    EventType.SAVE,
    EventType.MORE_LIKE,
    EventType.LESS_LIKE,
)


async def get_edition_out(session: AsyncSession, user_id: uuid.UUID, day: date) -> EditionOut:
    edition = await session.scalar(
        select(Edition).where(Edition.user_id == user_id, Edition.edition_date == day)
    )
    if edition is None:
        raise AppError(404, "edition_not_found", f"No edition for {day.isoformat()}")
    return await to_out(session, edition)


async def item_states(
    session: AsyncSession, user_id: uuid.UUID, item_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, ItemState]:
    """Fold the reader's events into one state per story: the latest event of each kind wins."""
    if not item_ids:
        return {}
    events = await session.execute(
        select(ReaderEvent.edition_item_id, ReaderEvent.type, ReaderEvent.value)
        .where(
            ReaderEvent.user_id == user_id,
            ReaderEvent.edition_item_id.in_(list(item_ids)),
            ReaderEvent.type.in_(_STATE_EVENTS),
        )
        .order_by(ReaderEvent.created_at, ReaderEvent.id)
    )
    states: dict[uuid.UUID, ItemState] = {}
    for item_id, kind, value in events:
        if item_id is None:
            continue
        state = states.setdefault(item_id, ItemState())
        on = value != 0
        if kind in (EventType.OPEN, EventType.MARK_READ):
            state.read = True
        elif kind is EventType.SKIP:
            state.skipped = on
        elif kind is EventType.SAVE:
            state.saved = on
        elif kind in (EventType.MORE_LIKE, EventType.LESS_LIKE):
            mine: Literal["more", "less"] = "more" if kind is EventType.MORE_LIKE else "less"
            if on:
                state.reaction = mine
            elif state.reaction == mine:
                state.reaction = None
    return states


def _item_out(
    item: EditionItem, article: Article, source: str | None, state: ItemState | None
) -> EditionItemOut:
    return EditionItemOut(
        id=item.id,
        article_id=article.id,
        section=item.section,
        position=item.position,
        slot=item.slot,
        headline=item.headline or article.title,
        summary=item.summary or article.summary or "",
        key_facts=fact_texts(article.key_facts),
        why_text=item.why_text,
        url=article.url,
        source=source or "Unknown source",
        image_url=article.image_url,
        published_at=article.published_at,
        score=item.score,
        score_breakdown=item.score_breakdown,
        state=state or ItemState(),
    )


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
    states = await item_states(session, edition.user_id, [item.id for item, _, _ in rows])
    items = [
        _item_out(item, article, source, states.get(item.id)) for item, article, source in rows
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


async def list_archive(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    before: date | None = None,
    limit: int = ARCHIVE_PAGE,
) -> list[EditionSummary]:
    """Finished editions, newest first; pass the last date seen as ``before`` for the next page."""
    query = select(Edition).where(Edition.user_id == user_id, Edition.status == EditionStatus.READY)
    if before is not None:
        query = query.where(Edition.edition_date < before)
    editions = await session.scalars(
        query.order_by(Edition.edition_date.desc()).limit(min(limit, ARCHIVE_MAX_PAGE))
    )
    return [
        EditionSummary(
            id=e.id,
            date=e.edition_date,
            number=e.number,
            title=e.title,
            item_count=int(e.stats.get("items", 0)),
            top_topics=[str(t) for t in e.stats.get("top_topics", [])][:TOP_TOPICS],
        )
        for e in editions
    ]


async def list_saved(session: AsyncSession, user_id: uuid.UUID) -> list[SavedItem]:
    """Every story the reader has saved (and not since un-saved), most recently saved first."""
    saves = await session.execute(
        select(ReaderEvent.edition_item_id, ReaderEvent.value)
        .where(
            ReaderEvent.user_id == user_id,
            ReaderEvent.type == EventType.SAVE,
            ReaderEvent.edition_item_id.is_not(None),
        )
        .order_by(ReaderEvent.created_at, ReaderEvent.id)
    )
    latest: dict[uuid.UUID, bool] = {}
    for item_id, value in saves:
        if item_id is not None:
            latest.pop(item_id, None)  # re-insert so dict order is "most recent event last"
            latest[item_id] = value != 0
    saved_ids = [item_id for item_id, on in reversed(latest.items()) if on]
    if not saved_ids:
        return []
    rows = (
        await session.execute(
            select(EditionItem, Article, Source.name, Edition.edition_date)
            .join(Edition, Edition.id == EditionItem.edition_id)
            .join(Article, Article.id == EditionItem.article_id)
            .outerjoin(Source, Source.id == Article.source_id)
            .where(Edition.user_id == user_id, EditionItem.id.in_(saved_ids))
        )
    ).all()
    states = await item_states(session, user_id, saved_ids)
    by_id = {
        item.id: SavedItem(
            **_item_out(item, article, source, states.get(item.id)).model_dump(),
            edition_date=day,
        )
        for item, article, source, day in rows
    }
    return [by_id[i] for i in saved_ids if i in by_id]


MAX_STORY_IMAGES = 4
MAX_STORY_SOURCES = 6
CLUSTER_WINDOW = timedelta(days=4)


async def get_story(session: AsyncSession, user_id: uuid.UUID, item_id: uuid.UUID) -> StoryOut:
    """One edition item with the pictures and outlets of the same story (its article's cluster)."""
    row = (
        await session.execute(
            select(EditionItem, Article, Source.name, Edition)
            .join(Edition, Edition.id == EditionItem.edition_id)
            .join(Article, Article.id == EditionItem.article_id)
            .outerjoin(Source, Source.id == Article.source_id)
            .where(EditionItem.id == item_id, Edition.user_id == user_id)
        )
    ).first()
    if row is None:
        raise AppError(404, "not_found", "That story is not in your paper")
    item, article, source_name, edition = row
    states = await item_states(session, user_id, [item.id])

    images = (
        [StoryImage(url=article.image_url, credit=source_name or "Unknown source")]
        if article.image_url
        else []
    )
    sources = [
        StorySource(
            name=source_name or "Unknown source",
            title=article.title,
            url=f"/r/{item.id}",
            published_at=article.published_at,
            primary=True,
        )
    ]
    if article.cluster_id is not None:
        query = (
            select(Article, Source.name)
            .outerjoin(Source, Source.id == Article.source_id)
            .where(Article.cluster_id == article.cluster_id, Article.id != article.id)
            .order_by(Article.published_at.desc().nulls_last())
        )
        anchor = article.published_at or article.fetched_at
        if anchor is not None:
            query = query.where(
                Article.published_at.between(anchor - CLUSTER_WINDOW, anchor + CLUSTER_WINDOW)
            )
        seen_outlets = {source_name}
        for other, other_source in (await session.execute(query.limit(30))).all():
            outlet = other_source or "Unknown source"
            if (
                other.image_url
                and len(images) < MAX_STORY_IMAGES
                and all(i.url != other.image_url for i in images)
            ):
                images.append(StoryImage(url=other.image_url, credit=outlet))
            if outlet not in seen_outlets and len(sources) < MAX_STORY_SOURCES:
                seen_outlets.add(outlet)
                sources.append(
                    StorySource(
                        name=outlet,
                        title=other.title,
                        url=other.url,
                        published_at=other.published_at,
                        primary=False,
                    )
                )
    return StoryOut(
        item=_item_out(item, article, source_name, states.get(item.id)),
        edition_id=edition.id,
        edition_date=edition.edition_date,
        edition_number=edition.number,
        author=article.author,
        images=images,
        sources=sources,
    )
