"""Enumerations stored as native Postgres enums (by value)."""

from enum import StrEnum

import sqlalchemy as sa


class Depth(StrEnum):
    BRIEF = "brief"
    BALANCED = "balanced"
    DEEP = "deep"


class SourceKind(StrEnum):
    RSS = "rss"
    GOOGLE_NEWS = "google_news"
    HACKERNEWS = "hackernews"
    ARXIV = "arxiv"
    REDDIT = "reddit"
    APIFY = "apify"


class EditionStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class Slot(StrEnum):
    LEAD = "lead"
    FEATURE = "feature"
    STANDARD = "standard"
    BRIEF = "brief"
    EXPLORE = "explore"


class EventType(StrEnum):
    IMPRESSION = "impression"
    OPEN = "open"
    DWELL = "dwell"
    SKIP = "skip"
    MORE_LIKE = "more_like"
    LESS_LIKE = "less_like"
    SAVE = "save"
    PDF_DOWNLOAD = "pdf_download"
    QUIZ_ANSWER = "quiz_answer"
    ONBOARDING_LIKE = "onboarding_like"
    ONBOARDING_SKIP = "onboarding_skip"
    ASK = "ask"
    MARK_READ = "mark_read"


class RunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


def pg_enum(enum_cls: type[StrEnum], name: str) -> sa.Enum:
    return sa.Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])
