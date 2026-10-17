from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.onboarding.limits import MAX_TEXT_CHARS


class SuggestionsOut(BaseModel):
    topic: str
    suggestions: list[str]


class ParseIn(BaseModel):
    text: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=3, max_length=MAX_TEXT_CHARS)
    ]


class ParsedTopic(BaseModel):
    slug: str
    weight: float = Field(ge=0, le=1)


class ParsedEntities(BaseModel):
    people: list[str] = Field(default_factory=list)
    companies: list[str] = Field(default_factory=list)
    teams: list[str] = Field(default_factory=list)
    places: list[str] = Field(default_factory=list)


class ParsedBlocked(BaseModel):
    topics: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class ParsedInterests(BaseModel):
    """What we heard in the reader's own words, shown back as editable chips."""

    topics: list[ParsedTopic] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    entities: ParsedEntities = Field(default_factory=ParsedEntities)
    blocked: ParsedBlocked = Field(default_factory=ParsedBlocked)
    context: str = ""
