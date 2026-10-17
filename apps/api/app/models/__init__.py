"""SQLAlchemy models. Importing this package registers every table on Base.metadata."""

from app.db.base import Base
from app.models.content import Article, DecodedLink, Source
from app.models.edition import Edition, EditionItem, PipelineRun, ReaderEvent
from app.models.enums import Depth, EditionStatus, EventType, RunStatus, Slot, SourceKind
from app.models.user import ReaderProfile, User

__all__ = [
    "Article",
    "Base",
    "DecodedLink",
    "Depth",
    "Edition",
    "EditionItem",
    "EditionStatus",
    "EventType",
    "PipelineRun",
    "ReaderEvent",
    "ReaderProfile",
    "RunStatus",
    "Slot",
    "Source",
    "SourceKind",
    "User",
]
