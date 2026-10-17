import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel

from app.models import EditionStatus, Slot


class ItemState(BaseModel):
    """What this reader has done with a story, folded from their events (latest event wins)."""

    read: bool = False
    saved: bool = False
    skipped: bool = False
    reaction: Literal["more", "less"] | None = None


class EditionItemOut(BaseModel):
    id: uuid.UUID
    article_id: uuid.UUID
    section: str
    position: int
    slot: Slot
    headline: str
    summary: str
    key_facts: list[str]
    why_text: str | None
    url: str
    source: str
    image_url: str | None
    published_at: datetime | None
    score: float | None
    score_breakdown: dict[str, Any]
    state: ItemState


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


class SavedItem(EditionItemOut):
    edition_date: date
