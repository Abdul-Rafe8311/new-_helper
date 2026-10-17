"""Onboarding endpoints: suggestions, free-text parsing, taste test, autosave, completion."""

from typing import Annotated

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, Query

from app.ai.llm import LLMError
from app.api.deps import (
    CurrentUser,
    EditionGeneratorDep,
    LLMDep,
    SessionDep,
    SettingsDep,
    current_user,
)
from app.core.errors import AppError
from app.onboarding import completion, service
from app.onboarding.parse import parse_interests
from app.onboarding.suggestions import suggestions_for
from app.schemas.onboarding import (
    CompleteOut,
    EditionStatusOut,
    HeadlinesOut,
    OnboardingStateOut,
    ParsedInterests,
    ParseIn,
    StepIn,
    SuggestionsOut,
    TasteAnswerIn,
)

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/onboarding", tags=["onboarding"], dependencies=[Depends(current_user)])


@router.get("/suggestions")
async def get_suggestions(
    topic: Annotated[str, Query(min_length=1, max_length=64)],
) -> SuggestionsOut:
    found = suggestions_for(topic)
    if found is None:
        raise AppError(404, "unknown_topic", f"No such topic: {topic}")
    return SuggestionsOut(topic=topic, suggestions=found)


@router.post("/parse")
async def parse(body: ParseIn, llm: LLMDep, settings: SettingsDep) -> ParsedInterests:
    try:
        return await parse_interests(llm, body.text, settings.llm_fast_model)
    except LLMError as exc:
        log.warning("onboarding_parse_failed", error=str(exc))
        raise AppError(502, "llm_failed", "We couldn't read that. Try rephrasing it.") from exc


@router.get("/state")
async def get_state(user: CurrentUser, session: SessionDep) -> OnboardingStateOut:
    return await service.get_state(session, user)


@router.put("/step/{number}")
async def put_step(
    number: int, body: StepIn, user: CurrentUser, session: SessionDep
) -> OnboardingStateOut:
    return await service.save_step(session, user, number, body)


@router.get("/headlines")
async def get_headlines(user: CurrentUser, session: SessionDep) -> HeadlinesOut:
    return await service.get_headlines(session, user)


@router.post("/taste", status_code=204)
async def post_taste(body: TasteAnswerIn, user: CurrentUser, session: SessionDep) -> None:
    await service.record_answer(session, user, body.article_id, body.interested)


@router.post("/complete")
async def complete(
    user: CurrentUser,
    session: SessionDep,
    generator: EditionGeneratorDep,
    background: BackgroundTasks,
) -> CompleteOut:
    """Build the profile and start the first edition; poll GET /onboarding/status for progress."""
    edition, run = await completion.complete_onboarding(session, user)
    if run:
        background.add_task(generator.generate, edition.id)
    return CompleteOut(edition_id=edition.id, status=edition.status.value)


@router.get("/status")
async def get_status(user: CurrentUser, session: SessionDep) -> EditionStatusOut:
    return await service.edition_status(session, user)
