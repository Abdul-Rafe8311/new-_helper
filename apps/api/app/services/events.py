"""Recording reader events."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Edition, EditionItem, EventType, ReaderEvent
from app.schemas.events import EventIn


async def owned_items(
    session: AsyncSession, user_id: uuid.UUID, item_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, tuple[uuid.UUID, uuid.UUID]]:
    """Of these edition items, the ones in the reader's own editions: id -> (edition, article)."""
    if not item_ids:
        return {}
    rows = await session.execute(
        select(EditionItem.id, EditionItem.edition_id, EditionItem.article_id)
        .join(Edition, Edition.id == EditionItem.edition_id)
        .where(Edition.user_id == user_id, EditionItem.id.in_(set(item_ids)))
    )
    return {item_id: (edition_id, article_id) for item_id, edition_id, article_id in rows}


async def record_events(
    session: AsyncSession, user_id: uuid.UUID, events: Sequence[EventIn]
) -> tuple[int, int]:
    """Bulk-insert the events that point at the reader's own stories; returns (accepted, rejected).

    Edition and article come from the item, never from the client, so a reader cannot write
    events against someone else's paper.
    """
    owned = await owned_items(session, user_id, [e.edition_item_id for e in events])
    # A batch is one transaction, so now() would stamp every row alike and lose the order the
    # reader acted in ("skip" then "undo skip"). Space the rows out by a microsecond each.
    start = datetime.now(UTC)
    rows = [
        ReaderEvent(
            user_id=user_id,
            edition_id=owned[e.edition_item_id][0],
            article_id=owned[e.edition_item_id][1],
            edition_item_id=e.edition_item_id,
            type=EventType(e.type),
            value=e.value,
            meta=e.meta,
            created_at=start + timedelta(microseconds=n),
        )
        for n, e in enumerate(events)
        if e.edition_item_id in owned
    ]
    session.add_all(rows)
    await session.commit()
    return len(rows), len(events) - len(rows)
