from datetime import UTC, datetime

from app.ingest.health import MAX_CONSECUTIVE_FAILURES, record_failure, record_success
from app.models import Source, SourceKind

NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)


def _source(**kwargs: object) -> Source:
    defaults: dict[str, object] = {
        "name": "Wire",
        "kind": SourceKind.RSS,
        "url": "https://wire.example.com/feed",
        "failure_count": 0,
        "active": True,
    }
    return Source(**{**defaults, **kwargs})


def test_five_consecutive_failures_deactivate_the_source() -> None:
    source = _source()
    results = [record_failure(source, NOW) for _ in range(MAX_CONSECUTIVE_FAILURES)]
    assert results == [False, False, False, False, True]
    assert source.active is False
    assert source.failure_count == 5


def test_four_failures_keep_it_active() -> None:
    source = _source()
    for _ in range(4):
        record_failure(source, NOW)
    assert source.active is True


def test_a_success_resets_the_streak() -> None:
    source = _source(failure_count=4)
    record_success(source, NOW, etag='"e"', last_modified="Fri")
    assert source.failure_count == 0
    assert source.etag == '"e"'
    assert source.last_fetched_at == NOW
    for _ in range(4):
        record_failure(source, NOW)
    assert source.active is True


def test_already_inactive_source_is_not_reported_twice() -> None:
    source = _source(active=False, failure_count=7)
    assert record_failure(source, NOW) is False
