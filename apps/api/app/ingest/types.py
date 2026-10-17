"""Plain data carried through the ingestion stage."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class RawItem:
    """One candidate article as a fetcher saw it, before full-text extraction."""

    url: str
    title: str
    published_at: datetime | None = None
    summary: str | None = None
    author: str | None = None
    image_url: str | None = None
    # Text a fetcher already has in full (e.g. an arXiv abstract); skips page extraction.
    content_text: str | None = None
    # Which registry source (or query) produced this item.
    origin: str = ""


@dataclass
class Extracted:
    """Result of full-text extraction for one page."""

    text: str
    title: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    image_url: str | None = None
    language: str | None = None


@dataclass
class IngestStats:
    fetched: int = 0
    new: int = 0
    duplicates: int = 0
    dropped: int = 0
    failed: int = 0
    sources_failed: int = 0
    sources_deactivated: int = 0
    timings: dict[str, float] = field(default_factory=dict)


@dataclass
class FetchResult:
    """What one fetcher returned, plus the HTTP validators to store for the next conditional GET."""

    items: list[RawItem] = field(default_factory=list)
    etag: str | None = None
    last_modified: str | None = None
    not_modified: bool = False
    # Items the fetcher saw but could not turn into usable candidates (e.g. undecodable links).
    skipped: int = 0
