"""Ingest service against a real Postgres, with fake fetchers/extractor (no network)."""

from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.ingest import service as service_module
from app.ingest.fetchers.base import FetchError
from app.ingest.http import RobotsDisallowedError
from app.ingest.service import FetchJob, IngestService
from app.ingest.types import Extracted, FetchResult, RawItem
from app.models import Article, PipelineRun, RunStatus, Source
from tests.conftest import TEST_SETTINGS
from tests.factories import make_source

pytestmark = pytest.mark.integration

NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)
BODY = " ".join(f"word{i}" for i in range(200))


@pytest.fixture
async def sessionmaker(engine: AsyncEngine) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Sessions that commit into savepoints of one transaction rolled back at the end."""
    async with engine.connect() as conn:
        trans = await conn.begin()
        yield async_sessionmaker(
            bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        await trans.rollback()


class FakeFetcher:
    def __init__(self, label: str, items: list[RawItem] | Exception) -> None:
        self.label = label
        self.items = items

    async def fetch(self) -> FetchResult:
        if isinstance(self.items, Exception):
            raise self.items
        return FetchResult(items=self.items, etag='"e1"')


class FakeExtractor:
    def __init__(self, pages: dict[str, Extracted | Exception | None]) -> None:
        self.pages = pages
        self.fetched: list[str] = []

    async def extract(self, url: str, *, high_value: bool = False) -> Extracted | None:
        self.fetched.append(url)
        page = self.pages.get(url, Extracted(text=BODY, language="en"))
        if isinstance(page, Exception):
            raise page
        return page


def _item(url: str, title: str = "A headline", hours_old: float = 2, **kw: Any) -> RawItem:
    return RawItem(url=url, title=title, published_at=NOW - timedelta(hours=hours_old), **kw)


def _service(
    sm: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
    source: Source,
    fetchers: Sequence[FakeFetcher],
    extractor: FakeExtractor,
) -> IngestService:
    monkeypatch.setattr(
        service_module,
        "build_jobs",
        lambda *a, **k: [FetchJob(source, f) for f in fetchers],
    )
    return IngestService(
        TEST_SETTINGS,
        sm,
        http=None,  # type: ignore[arg-type]
        extractor=extractor,  # type: ignore[arg-type]
        resolver=None,  # type: ignore[arg-type]
        clock=lambda: NOW,
    )


async def _count(sm: async_sessionmaker[AsyncSession]) -> int:
    async with sm() as session:
        return int(await session.scalar(select(func.count()).select_from(Article)) or 0)


async def test_stores_articles_and_records_the_run(
    sessionmaker: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    async with sessionmaker() as s:
        source = await make_source(s)
        await s.commit()
    fetcher = FakeFetcher(
        "feed", [_item("https://www.a.test/one?utm_source=x", author="Sam", image_url="i.jpg")]
    )
    stats = await _service(sessionmaker, monkeypatch, source, [fetcher], FakeExtractor({})).run()

    assert (stats.fetched, stats.new, stats.duplicates, stats.failed) == (1, 1, 0, 0)
    async with sessionmaker() as s:
        article = (await s.scalars(select(Article))).one()
        assert article.url == "https://a.test/one"
        assert article.source_id == source.id
        assert article.word_count == 200
        assert article.language == "en"
        assert article.author == "Sam"
        assert article.excerpt is not None
        assert len(article.excerpt) <= 301
        assert article.content_hash is not None
        assert len(article.content_hash) == 64
        run = (await s.scalars(select(PipelineRun))).one()
        assert run.stage == "ingest"
        assert run.status == RunStatus.SUCCEEDED
        assert run.stats["new"] == 1
        assert "feed" in run.stats["timings"]
        refreshed = await s.get(Source, source.id)
        assert refreshed is not None
        assert refreshed.etag == '"e1"'
        assert refreshed.failure_count == 0


async def test_second_run_skips_known_urls_and_never_refetches_them(
    sessionmaker: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    async with sessionmaker() as s:
        source = await make_source(s)
        await s.commit()
    items = [_item("https://a.test/one"), _item("https://a.test/two", title="Other")]
    extractor = FakeExtractor({"https://a.test/two": Extracted(text="other " * 150, language="en")})
    svc = _service(sessionmaker, monkeypatch, source, [FakeFetcher("feed", items)], extractor)
    await svc.run()
    extractor.fetched.clear()
    stats = await svc.run()
    assert (stats.new, stats.duplicates) == (0, 2)
    assert extractor.fetched == []
    assert await _count(sessionmaker) == 2


async def test_same_story_under_a_new_url_is_deduped_by_content_hash(
    sessionmaker: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    async with sessionmaker() as s:
        source = await make_source(s)
        await s.commit()
    items = [
        _item("https://a.test/story", title="Big news"),
        _item("https://b.test/copy", title="Big news"),
    ]
    stats = await _service(
        sessionmaker, monkeypatch, source, [FakeFetcher("f", items)], FakeExtractor({})
    ).run()
    assert (stats.new, stats.duplicates) == (1, 1)
    assert await _count(sessionmaker) == 1


async def test_stale_short_and_foreign_language_items_are_dropped(
    sessionmaker: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    async with sessionmaker() as s:
        source = await make_source(s)
        await s.commit()
    items = [
        _item("https://a.test/old", hours_old=72),
        _item("https://a.test/short", title="Short"),
        _item("https://a.test/german", title="German"),
        _item("https://a.test/ok", title="Fine"),
    ]
    extractor = FakeExtractor(
        {
            "https://a.test/short": Extracted(text="too few words here", language="en"),
            "https://a.test/german": Extracted(text=BODY, language="de"),
            "https://a.test/ok": Extracted(text="fine " * 150, language="en"),
        }
    )
    stats = await _service(
        sessionmaker, monkeypatch, source, [FakeFetcher("f", items)], extractor
    ).run()
    assert stats.new == 1
    assert dict(stats.drop_reasons) == {"short": 1, "language": 1}
    assert "https://a.test/old" not in extractor.fetched  # stale items are never downloaded


async def test_extraction_problems_are_counted_not_fatal(
    sessionmaker: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    async with sessionmaker() as s:
        source = await make_source(s)
        await s.commit()
    items = [
        _item("https://a.test/blocked", title="Blocked"),
        _item("https://a.test/broken", title="Broken"),
        _item("https://a.test/empty", title="Empty"),
        _item("https://a.test/fine", title="Fine"),
    ]
    extractor = FakeExtractor(
        {
            "https://a.test/blocked": RobotsDisallowedError("x"),
            "https://a.test/broken": RuntimeError("parser exploded"),
            "https://a.test/empty": None,
            "https://a.test/fine": Extracted(text="fine " * 150, language="en"),
        }
    )
    stats = await _service(
        sessionmaker, monkeypatch, source, [FakeFetcher("f", items)], extractor
    ).run()
    assert stats.new == 1
    assert stats.failed == 1
    assert stats.drop_reasons["robots"] == 1


async def test_source_is_deactivated_after_five_failed_runs_and_success_resets(
    sessionmaker: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    async with sessionmaker() as s:
        source = await make_source(s)
        await s.commit()
    broken = FakeFetcher("feed", FetchError("HTTP 500"))
    svc = _service(sessionmaker, monkeypatch, source, [broken], FakeExtractor({}))
    for _ in range(4):
        stats = await svc.run()
    assert stats.sources_failed == 1
    async with sessionmaker() as s:
        assert (await s.get(Source, source.id)).failure_count == 4  # type: ignore[union-attr]

    broken.items = []  # the feed recovers
    await svc.run()
    async with sessionmaker() as s:
        recovered = await s.get(Source, source.id)
        assert recovered is not None
        assert recovered.failure_count == 0
        assert recovered.active

    broken.items = FetchError("down again")
    for _ in range(5):
        stats = await svc.run()
    assert stats.sources_deactivated == 1
    async with sessionmaker() as s:
        dead = await s.get(Source, source.id)
        assert dead is not None
        assert dead.active is False


async def test_a_source_with_several_jobs_only_fails_when_all_of_them_fail(
    sessionmaker: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    async with sessionmaker() as s:
        source = await make_source(s)
        await s.commit()
    fetchers = [
        FakeFetcher("q1", FetchError("429")),
        FakeFetcher("q2", [_item("https://a.test/x")]),
    ]
    await _service(sessionmaker, monkeypatch, source, fetchers, FakeExtractor({})).run()
    async with sessionmaker() as s:
        assert (await s.get(Source, source.id)).failure_count == 0  # type: ignore[union-attr]


async def test_a_crash_marks_the_run_failed(
    sessionmaker: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*a: object, **k: object) -> list[FetchJob]:
        raise RuntimeError("cannot build jobs")

    monkeypatch.setattr(service_module, "build_jobs", boom)
    svc = IngestService(
        TEST_SETTINGS,
        sessionmaker,
        None,
        None,
        None,
        clock=lambda: NOW,  # type: ignore[arg-type]
    )
    with pytest.raises(RuntimeError, match="cannot build jobs"):
        await svc.run()
    async with sessionmaker() as s:
        run = (await s.scalars(select(PipelineRun))).one()
        assert run.status == RunStatus.FAILED
