from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.core.taxonomy import TOPIC_SLUGS
from app.models import Depth

Term = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Terms = Annotated[list[Term], Field(max_length=100)]


class Entities(BaseModel):
    people: Terms = []
    companies: Terms = []
    teams: Terms = []
    places: Terms = []


class Blocked(BaseModel):
    topics: Terms = []
    keywords: Terms = []
    sources: Terms = []


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    onboarding_completed: bool
    topics: dict[str, float]
    keywords: list[str]
    entities: Entities
    blocked: Blocked
    source_affinity: dict[str, Any]
    reading_minutes: int
    depth: Depth
    surprise_me: bool
    paper_name: str | None
    context_notes: str | None


class ProfileUpdate(BaseModel):
    """Fields left out are unchanged. source_affinity and interest_vector are learned, not set."""

    model_config = ConfigDict(extra="forbid")

    onboarding_completed: bool | None = None
    topics: dict[str, Annotated[float, Field(ge=0, le=1)]] | None = None
    keywords: Terms | None = None
    entities: Entities | None = None
    blocked: Blocked | None = None
    reading_minutes: Annotated[int, Field(ge=5, le=60)] | None = None
    depth: Depth | None = None
    surprise_me: bool | None = None
    paper_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] | None = (
        None
    )
    context_notes: Annotated[str, Field(max_length=2000)] | None = None

    @field_validator("topics")
    @classmethod
    def known_topics(cls, value: dict[str, float] | None) -> dict[str, float] | None:
        if value is not None and (unknown := sorted(set(value) - TOPIC_SLUGS)):
            raise ValueError(f"unknown topics: {', '.join(unknown)}")
        return value
