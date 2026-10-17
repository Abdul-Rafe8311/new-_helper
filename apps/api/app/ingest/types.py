"""Plain data carried through the ingestion stage."""

from collections import Counter
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
    fetched: int = 0  # raw items returned by fetchers
    new: int = 0  # articles inserted
    duplicates: int = 0  # known URL/content hash or repeated in the batch
    dropped: int = 0  # stale / short / wrong language / robots / undecodable links
    failed: int = 0  # extraction errors
    sources_failed: int = 0  # fetch jobs that raised
    sources_deactivated: int = 0
    drop_reasons: Counter[str] = field(default_factory=Counter)
    timings: dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "fetched": self.fetched,
            "new": self.new,
            "duplicates": self.duplicates,
            "dropped": self.dropped,
            "failed": self.failed,
            "sources_failed": self.sources_failed,
            "sources_deactivated": self.sources_deactivated,
            "drop_reasons": {str(k): v for k, v in self.drop_reasons.items()},
            "timings": self.timings,
        }


@dataclass
class FetchResult:
    """What one fetcher returned, plus the HTTP validators to store for the next conditional GET."""

    items: list[RawItem] = field(default_factory=list)
    etag: str | None = None
    last_modified: str | None = None
    not_modified: bool = False
    # Items the fetcher saw but could not turn into usable candidates (e.g. undecodable links).
    skipped: int = 0
