"""Reader behaviour events feeding the learning loop (T11). The reader batches them every 10s."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, SessionDep, current_user
from app.core.errors import AppError
from app.core.ratelimit import SlidingWindowLimiter
from app.schemas.events import EventsIn, EventsOut
from app.services.events import record_events

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
async def post_events(body: EventsIn, user: CurrentUser, session: SessionDep) -> EventsOut:
    accepted, rejected = await record_events(session, user.id, body.events)
    return EventsOut(accepted=accepted, rejected=rejected)
