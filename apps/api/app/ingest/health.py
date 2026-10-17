"""Source health: consecutive failures deactivate a source so one dead feed stops costing time."""

from datetime import datetime

from app.models import Source

MAX_CONSECUTIVE_FAILURES = 5


def record_success(
    source: Source, now: datetime, *, etag: str | None, last_modified: str | None
) -> None:
    source.failure_count = 0
    source.last_fetched_at = now
    # Keep the old validators on a 304 (fetchers echo them back) and take new ones otherwise.
    source.etag = etag
    source.last_modified = last_modified


def record_failure(source: Source, now: datetime) -> bool:
    """Count a failed fetch. Returns True when this failure deactivated the source."""
    source.failure_count += 1
    source.last_fetched_at = now
    if source.active and source.failure_count >= MAX_CONSECUTIVE_FAILURES:
        source.active = False
        return True
    return False
