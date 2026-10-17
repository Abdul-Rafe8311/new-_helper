from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# What the browser may report. Server-side events (pdf_download, ask, ...) are not accepted here.
ClientEventType = Literal[
    "impression", "dwell", "skip", "more_like", "less_like", "save", "mark_read", "quiz_answer"
]

MAX_EVENTS_PER_REQUEST = 100
MAX_DWELL_SECONDS = 3600.0


class EventIn(BaseModel):
    """One thing the reader did to one story.

    ``value`` carries the measurement: seconds for ``dwell``; for the toggles (``skip``,
    ``save``, ``more_like``, ``less_like``) ``0`` retracts an earlier event and anything else
    (or nothing) sets it. A ``quiz_answer`` carries ``1`` (correct) or ``0`` (wrong) and, in
    ``meta``, ``q`` (the question's position) and ``kind`` (``quiz`` for today's questions,
    ``recall`` for "Still remember?"); it is tied to the story the question was about.
    """

    type: ClientEventType
    edition_item_id: UUID
    value: float | None = Field(default=None, ge=0, le=MAX_DWELL_SECONDS)
    meta: dict[str, str | int | float | bool | None] = Field(default_factory=dict, max_length=8)

    @field_validator("meta")
    @classmethod
    def _short_strings(
        cls, meta: dict[str, str | int | float | bool | None]
    ) -> dict[str, str | int | float | bool | None]:
        if any(isinstance(v, str) and len(v) > 200 for v in meta.values()):
            raise ValueError("meta strings are limited to 200 characters")
        return meta


class EventsIn(BaseModel):
    events: list[EventIn] = Field(min_length=1, max_length=MAX_EVENTS_PER_REQUEST)


class EventsOut(BaseModel):
    accepted: int
    rejected: int
