"""Reader behaviour events feeding the learning loop (T11). The reader batches them every 10s."""

from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.deps import BackgroundSessionmakerDep, CurrentUser, SessionDep, current_user
from app.core.errors import AppError
from app.core.ratelimit import SlidingWindowLimiter
from app.personalize.learn_service import learn_after_events
from app.schemas.events import EventsIn, EventsOut
from app.services.events import record_events

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/events", tags=["events"], dependencies=[Depends(current_user)])

# The reader sends one batch per 10s (plus one when the tab hides); this leaves room for a few tabs.
_limiter = SlidingWindowLimiter(limit=30, window_seconds=60)


def events_limiter() -> SlidingWindowLimiter:
    return _limiter


async def rate_limit(
    user: CurrentUser, limiter: Annotated[SlidingWindowLimiter, Depends(events_limiter)]
) -> None:
    retry_after = limiter.hit(str(user.id))
    if retry_after is not None:
        raise AppError(429, "rate_limited", f"Too many event batches; retry in {retry_after:.0f}s")


@router.post("", response_model=EventsOut, dependencies=[Depends(rate_limit)])
async def post_events(
    body: EventsIn,
    user: CurrentUser,
    session: SessionDep,
    background: BackgroundTasks,
    sessionmaker: BackgroundSessionmakerDep,
) -> EventsOut:
    accepted, rejected = await record_events(session, user.id, body.events)
    if accepted:
        # more_like / less_like / save are strong enough to learn from right away; the rest waits
        # for the nightly run. Runs after the response so the reader never waits on it.
        background.add_task(_learn, sessionmaker, user.id, [e.type for e in body.events])
    return EventsOut(accepted=accepted, rejected=rejected)


async def _learn(
    sessionmaker: async_sessionmaker[AsyncSession], user_id: UUID, event_types: list[str]
) -> None:
    try:
        await learn_after_events(sessionmaker, user_id, event_types)
    except Exception:  # the events are stored; the nightly run will pick them up
        log.exception("incremental_learn_failed", user_id=str(user_id))
