from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator

from app.core.taxonomy import TOPIC_SLUGS


class TopicWeight(BaseModel):
    slug: str
    label: str
    weight: float


class LearnedEntity(BaseModel):
    id: str
    kind: str
    name: str
    pinned: bool


class BlockedTopic(BaseModel):
    topic: str
    label: str


class InterestsOut(BaseModel):
    topics: list[TopicWeight]
    entities: list[LearnedEntity]
    blocked: list[BlockedTopic]
    # true until the reader has produced any learning or edit, so the page can explain itself
    is_new: bool


class TopicsIn(BaseModel):
    topics: dict[str, Annotated[float, Field(ge=0, le=1)]] = Field(min_length=1, max_length=60)

    @field_validator("topics")
    @classmethod
    def known_topics(cls, value: dict[str, float]) -> dict[str, float]:
        if unknown := sorted(set(value) - TOPIC_SLUGS):
            raise ValueError(f"unknown topics: {', '.join(unknown)}")
        return value


class PinIn(BaseModel):
    pinned: bool = True


class BlockedIn(BaseModel):
    topic: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)]

    @field_validator("topic")
    @classmethod
    def known_topic(cls, value: str) -> str:
        if value not in TOPIC_SLUGS:
            raise ValueError(f"unknown topic: {value}")
        return value


class TimelineEntry(BaseModel):
    id: str
    at: str
    kind: str
    text: str


class TimelineDay(BaseModel):
    date: str
    entries: list[TimelineEntry]


class TimelineOut(BaseModel):
    days: list[TimelineDay]
