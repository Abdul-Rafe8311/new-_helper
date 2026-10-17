"""The reader's interests page: what was learned, and edits to it."""

from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.schemas.interests import (
    BlockedIn,
    BlockedSourceIn,
    InterestsOut,
    PinIn,
    TimelineOut,
    TopicsIn,
)
from app.services import interests as service

router = APIRouter(prefix="/me/interests", tags=["interests"])


@router.get("")
async def get_interests(user: CurrentUser, session: SessionDep) -> InterestsOut:
    return await service.get_interests(session, user.profile)


@router.put("/topics")
async def put_topics(body: TopicsIn, user: CurrentUser, session: SessionDep) -> InterestsOut:
    return await service.set_topics(session, user.profile, body.topics)


@router.post("/entities/{entity_id}/pin")
async def pin_entity(
    entity_id: str, user: CurrentUser, session: SessionDep, body: PinIn | None = None
) -> InterestsOut:
    return await service.pin_entity(session, user.profile, entity_id, body.pinned if body else True)


@router.delete("/entities/{entity_id}")
async def delete_entity(entity_id: str, user: CurrentUser, session: SessionDep) -> InterestsOut:
    return await service.remove_entity(session, user.profile, entity_id)


@router.post("/blocked")
async def post_blocked(body: BlockedIn, user: CurrentUser, session: SessionDep) -> InterestsOut:
    return await service.block_topic(session, user.profile, body.topic)


@router.delete("/blocked/{topic}")
async def delete_blocked(topic: str, user: CurrentUser, session: SessionDep) -> InterestsOut:
    return await service.unblock_topic(session, user.profile, topic)


@router.post("/blocked-sources")
async def post_blocked_source(
    body: BlockedSourceIn, user: CurrentUser, session: SessionDep
) -> InterestsOut:
    return await service.block_source(session, user.profile, body.source)


@router.delete("/blocked-sources/{source}")
async def delete_blocked_source(
    source: str, user: CurrentUser, session: SessionDep
) -> InterestsOut:
    return await service.unblock_source(session, user.profile, source)


@router.post("/reset")
async def post_reset(user: CurrentUser, session: SessionDep) -> InterestsOut:
    return await service.reset_interests(session, user.profile)


@router.get("/timeline")
async def get_timeline(user: CurrentUser, session: SessionDep) -> TimelineOut:
    return await service.timeline(session, user)
