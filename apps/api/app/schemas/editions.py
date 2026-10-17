import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel

from app.models import EditionStatus, Slot


class EditionItemOut(BaseModel):
    id: uuid.UUID
    article_id: uuid.UUID
    section: str
    position: int
    slot: Slot
    headline: str
    summary: str
    why_text: str | None
    url: str
    source: str
    image_url: str | None
    published_at: datetime | None
    score: float | None
    score_breakdown: dict[str, Any]


class EditionOut(BaseModel):
    id: uuid.UUID
    date: date
    number: int
    status: EditionStatus
    title: str | None
    editor_note: str | None
    layout: dict[str, Any]
    items: list[EditionItemOut]
    stats: dict[str, Any]
    generated_at: datetime | None


class EditionSummary(BaseModel):
    id: uuid.UUID
    date: date
    number: int
    title: str | None
    item_count: int
    top_topics: list[str]
