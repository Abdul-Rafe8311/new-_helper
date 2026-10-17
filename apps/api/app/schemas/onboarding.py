from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import available_timezones

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.core.taxonomy import TOPIC_SLUGS
from app.models import Depth
from app.onboarding.limits import MAX_TEXT_CHARS, MIN_TOPICS


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


Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class _Step(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NameStep(_Step):
    """Step 1: the paper's name and where the reader is."""

    paper_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)
    ]
    city: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] | None = None
    timezone: Annotated[str, StringConstraints(max_length=64)]

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value: str) -> str:
        if value not in available_timezones():
            raise ValueError(f"unknown timezone: {value}")
        return value


class BeatsStep(_Step):
    """Step 2: chosen topics, and the sub-interests picked under "Go deeper"."""

    topics: Annotated[list[str], Field(min_length=MIN_TOPICS, max_length=len(TOPIC_SLUGS))]
    deeper: dict[str, Annotated[list[Label], Field(max_length=12)]] = Field(default_factory=dict)

    @field_validator("topics")
    @classmethod
    def known_unique_topics(cls, value: list[str]) -> list[str]:
        if unknown := sorted(set(value) - TOPIC_SLUGS):
            raise ValueError(f"unknown topics: {', '.join(unknown)}")
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def deeper_only_for_chosen_topics(self) -> "BeatsStep":
        if stray := sorted(set(self.deeper) - set(self.topics)):
            raise ValueError(f"sub-interests for topics that are not chosen: {', '.join(stray)}")
        return self


class WordsStep(_Step):
    """Step 3: the reader's own words and the (edited) chips parsed from them."""

    text: Annotated[str, StringConstraints(strip_whitespace=True, max_length=MAX_TEXT_CHARS)]
    parsed: ParsedInterests | None = None

    @field_validator("parsed")
    @classmethod
    def sane_chips(cls, value: ParsedInterests | None) -> ParsedInterests | None:
        if value is None:
            return value
        slugs = {t.slug for t in value.topics} | set(value.blocked.topics)
        if unknown := sorted(slugs - TOPIC_SLUGS):
            raise ValueError(f"unknown topics: {', '.join(unknown)}")
        terms = [*value.keywords, *value.blocked.keywords]
        terms += [e for group in value.entities.model_dump().values() for e in group]
        if len(terms) > 120 or any(not 0 < len(t) <= 80 for t in terms):
            raise ValueError("chips must be 1-80 characters, at most 120 in total")
        return value


class TasteStep(_Step):
    """Step 4: how many headlines were answered; the answers themselves are events."""

    answered: Annotated[int, Field(ge=0, le=50)]


class ReadingStep(_Step):
    """Step 5: how the reader reads."""

    reading_minutes: Literal[5, 10, 20]
    depth: Depth = Depth.BALANCED
    surprise_me: bool = True


StepIn = NameStep | BeatsStep | WordsStep | TasteStep | ReadingStep


class OnboardingStateOut(BaseModel):
    """Everything saved so far, so a refresh resumes where the reader left off."""

    step: int = Field(ge=1, le=6, description="The step to resume at (6 is the finale).")
    completed: bool
    name: NameStep | None = None
    beats: BeatsStep | None = None
    words: WordsStep | None = None
    reading: ReadingStep | None = None
    answers: dict[UUID, bool] = Field(
        default_factory=dict, description="Taste test answers by article id; true = interested."
    )


class HeadlineOut(BaseModel):
    id: UUID
    headline: str
    source: str
    image_url: str | None
    topic: str | None
    outside: bool = Field(description="True for the few picks outside the reader's chosen topics.")
    answer: bool | None = None


class HeadlinesOut(BaseModel):
    headlines: list[HeadlineOut]


class TasteAnswerIn(BaseModel):
    article_id: UUID
    interested: bool
