import uuid
from datetime import UTC, datetime, timedelta

from app.ingest.fetchers.base import FetchError
from app.ingest.service import (
    Candidate,
    FetchJob,
    JobOutcome,
    interleave_by_domain,
    select_candidates,
)
from app.ingest.types import FetchResult, RawItem
from app.models import Source, SourceKind

NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)


class _Fetcher:
    label = "f"

    async def fetch(self) -> FetchResult:  # pragma: no cover - never run in these tests
        raise FetchError("unused")


def _outcome(items: list[RawItem], *, high_value: bool = False) -> JobOutcome:
    source = Source(
        id=uuid.uuid4(),
        name="S",
        kind=SourceKind.RSS,
        url=f"https://s{uuid.uuid4().hex[:6]}.test/feed",
        high_value=high_value,
    )
    return JobOutcome(FetchJob(source, _Fetcher()), FetchResult(items=items), None, 0.1)


def _item(url: str, hours_old: float = 1, title: str = "T") -> RawItem:
    return RawItem(url=url, title=title, published_at=NOW - timedelta(hours=hours_old))


def test_candidates_drop_stale_and_dedupe_by_canonical_url() -> None:
    outcomes = [
        _outcome([_item("https://www.a.test/x?utm_source=1"), _item("https://a.test/old", 60)]),
        _outcome([_item("https://a.test/x/"), _item("https://b.test/y")]),
    ]
    candidates, seen, duplicates = select_candidates(outcomes, NOW)
    assert [c.url for c in candidates] == ["https://a.test/x", "https://b.test/y"]
    assert seen == 4
    assert duplicates == 1


def test_per_fetcher_cap_keeps_the_newest() -> None:
    items = [_item(f"https://a.test/{i}", hours_old=i) for i in range(10)]
    candidates, _, _ = select_candidates([_outcome(items)], NOW, per_fetcher=3)
    assert [c.url for c in candidates] == [f"https://a.test/{i}" for i in range(3)]


def test_failed_fetches_contribute_nothing_and_flags_carry_over() -> None:
    failed = _outcome([])
    failed.result = None
    failed.error = "boom"
    ok = _outcome([_item("https://a.test/x")], high_value=True)
    candidates, _, _ = select_candidates([failed, ok], NOW)
    assert len(candidates) == 1
    assert candidates[0].high_value is True
    assert candidates[0].source_id == ok.job.source.id  # type: ignore[union-attr]


def test_interleave_round_robins_domains() -> None:
    def cand(url: str) -> Candidate:
        return Candidate(_item(url), url, None, False)

    urls = ["https://a.test/1", "https://a.test/2", "https://a.test/3", "https://b.test/1"]
    ordered = [c.url for c in interleave_by_domain([cand(u) for u in urls])]
    assert ordered == [
        "https://a.test/1",
        "https://b.test/1",
        "https://a.test/2",
        "https://a.test/3",
    ]
