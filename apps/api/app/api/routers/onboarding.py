"""Onboarding endpoints: suggestions, free-text parsing, taste test, autosave, completion."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import current_user
from app.core.errors import AppError
from app.onboarding.suggestions import suggestions_for
from app.schemas.onboarding import SuggestionsOut

router = APIRouter(prefix="/onboarding", tags=["onboarding"], dependencies=[Depends(current_user)])


@router.get("/suggestions")
async def get_suggestions(
    topic: Annotated[str, Query(min_length=1, max_length=64)],
) -> SuggestionsOut:
    found = suggestions_for(topic)
    if found is None:
        raise AppError(404, "unknown_topic", f"No such topic: {topic}")
    return SuggestionsOut(topic=topic, suggestions=found)
