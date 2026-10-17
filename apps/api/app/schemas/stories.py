import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.editions import EditionItemOut


class StoryImage(BaseModel):
    url: str
    credit: str  # the outlet the picture came from


class StorySource(BaseModel):
    name: str
    title: str
    url: str
    published_at: datetime | None
    primary: bool  # the article this story was written from; its link logs an open


class StoryOut(BaseModel):
    item: EditionItemOut
    edition_id: uuid.UUID
    edition_date: date
    edition_number: int
    author: str | None
    images: list[StoryImage]
    sources: list[StorySource]
