"""Onboarding endpoints: suggestions, free-text parsing, taste test, autosave, completion."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query

from app.ai.llm import LLMError
from app.api.deps import LLMDep, SettingsDep, current_user
from app.core.errors import AppError
from app.onboarding.parse import parse_interests
from app.onboarding.suggestions import suggestions_for
from app.schemas.onboarding import ParsedInterests, ParseIn, SuggestionsOut

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
