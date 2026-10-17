"""The ingest stage: fetch everywhere, extract, filter, dedupe, upsert, and record the run.

    sources + reader interests -> fetchers (concurrent) -> candidates -> full text -> Articles

Per-article work happens once and is shared by every reader. Nothing here calls an LLM.
"""

import asyncio
import time
import uuid
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.ingest.extract import ArticleExtractor, make_excerpt, word_count
from app.ingest.fetchers.apify import ActorRunner, ApifyLinkDecoder, ApifyPageExtractor
from app.ingest.fetchers.arxiv import ArxivFetcher, Throttle, category_from_url
from app.ingest.fetchers.base import Fetcher
from app.ingest.fetchers.google_news import (
    GoogleNewsDecoder,
    GoogleNewsFetcher,
    LinkResolver,
    Locale,
)
from app.ingest.fetchers.hackernews import HackerNewsFetcher
from app.ingest.fetchers.reddit import RedditFetcher
from app.ingest.fetchers.rss import RssFetcher
from app.ingest.health import record_failure, record_success
from app.ingest.http import PoliteClient, RobotsDisallowedError
from app.ingest.link_cache import DbLinkCache
from app.ingest.normalise import DropReason, content_hash, drop_reason, is_stale
from app.ingest.queries import ReaderInterests, build_queries
from app.ingest.types import Extracted, FetchResult, IngestStats, RawItem
from app.ingest.urls import canonicalize_url, domain_of
from app.models import Article, PipelineRun, ReaderProfile, RunStatus, Source, SourceKind, User

log = structlog.get_logger(__name__)

MAX_ITEMS_PER_FETCHER = 40
EXTRACT_CONCURRENCY = 24
INSERT_CHUNK = 100

Clock = Callable[[], datetime]


@dataclass(frozen=True)
class FetchJob:
    source: Source | None
    fetcher: Fetcher


@dataclass
class JobOutcome:
    job: FetchJob
    result: FetchResult | None
    error: str | None
    seconds: float


@dataclass(frozen=True)
class Candidate:
    item: RawItem
    url: str  # canonical, what we store and dedupe on
    source_id: uuid.UUID | None
    high_value: bool


def build_jobs(
    sources: Iterable[Source],
    google_queries: Sequence[tuple[str, Locale]],
    *,
    http: PoliteClient,
    resolver: LinkResolver,
    settings: Settings,
) -> list[FetchJob]:
    """One fetch job per feed, API source and Google News query."""
    throttle = Throttle()
    jobs: list[FetchJob] = []
    for source in sources:
        if not source.active:
            continue
        match source.kind:
            case SourceKind.RSS:
                fetcher: Fetcher = RssFetcher(
                    http,
                    source.url,
                    source.name,
                    etag=source.etag,
                    last_modified=source.last_modified,
                )
                jobs.append(FetchJob(source, fetcher))
            case SourceKind.HACKERNEWS:
                jobs.append(FetchJob(source, HackerNewsFetcher(http)))
            case SourceKind.ARXIV:
                jobs.append(
                    FetchJob(source, ArxivFetcher(http, category_from_url(source.url), throttle))
                )
            case SourceKind.GOOGLE_NEWS:
                jobs.extend(
                    FetchJob(source, GoogleNewsFetcher(http, resolver, text, locale))
                    for text, locale in google_queries
                )
            case SourceKind.REDDIT if settings.reddit_enabled:
                jobs.extend(
                    FetchJob(source, RedditFetcher(http, sub)) for sub in settings.reddit_subreddits
                )
            case _:
                continue
    return jobs


def select_candidates(
    outcomes: Iterable[JobOutcome], now: datetime, per_fetcher: int = MAX_ITEMS_PER_FETCHER
) -> tuple[list[Candidate], int, int]:
    """Canonicalise, drop already-stale items, cap each fetcher, dedupe URLs in the batch.

    Returns (candidates, items_seen, duplicate_urls).
    """
    seen_urls: set[str] = set()
    candidates: list[Candidate] = []
    seen = duplicates = 0
    for outcome in outcomes:
        if outcome.result is None:
            continue
        epoch = datetime.min.replace(tzinfo=UTC)
        fresh = sorted(
            (i for i in outcome.result.items if not is_stale(i.published_at, now)),
            key=lambda i: i.published_at or epoch,
            reverse=True,
        )
        seen += len(outcome.result.items)
        for item in fresh[:per_fetcher]:
            url = canonicalize_url(item.url)
            if url in seen_urls:
                duplicates += 1
                continue
            seen_urls.add(url)
            source = outcome.job.source
            candidates.append(
                Candidate(
                    item, url, source.id if source else None, bool(source and source.high_value)
                )
            )
    return candidates, seen, duplicates


def interleave_by_domain(candidates: Sequence[Candidate]) -> list[Candidate]:
    """Round-robin across domains so a slow, busy domain cannot hog the extraction slots."""
    queues: dict[str, list[Candidate]] = {}
    for candidate in candidates:
        queues.setdefault(domain_of(candidate.url), []).append(candidate)
    ordered: list[Candidate] = []
    while queues:
        for domain in list(queues):
            ordered.append(queues[domain].pop(0))
            if not queues[domain]:
                del queues[domain]
    return ordered


class IngestService:
    def __init__(
        self,
        settings: Settings,
        sessionmaker: async_sessionmaker[AsyncSession],
        http: PoliteClient,
        extractor: ArticleExtractor,
        resolver: LinkResolver,
        clock: Clock = lambda: datetime.now(UTC),
    ) -> None:
        self._settings = settings
        self._sessionmaker = sessionmaker
        self._http = http
        self._extractor = extractor
        self._resolver = resolver
        self._clock = clock

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        sessionmaker: async_sessionmaker[AsyncSession],
        http: PoliteClient,
        runner: ActorRunner | None = None,
    ) -> "IngestService":
        """Open-source by default; Apify decoders/extractors only when a runner is supplied."""
        fallback = ApifyLinkDecoder(runner, settings.apify_gnews_actor) if runner else None
        page_fallback = ApifyPageExtractor(runner, settings.apify_extract_actor) if runner else None
        resolver = LinkResolver(DbLinkCache(sessionmaker), GoogleNewsDecoder(), fallback)
        return cls(settings, sessionmaker, http, ArticleExtractor(http, page_fallback), resolver)

    async def run(self) -> IngestStats:
        stats = IngestStats()
        started = time.monotonic()
        run_id = await self._start_run()
        try:
            await self._ingest(stats)
        except BaseException:
            await self._finish_run(run_id, RunStatus.FAILED, stats, time.monotonic() - started)
            raise
        await self._finish_run(run_id, RunStatus.SUCCEEDED, stats, time.monotonic() - started)
        return stats

    async def _ingest(self, stats: IngestStats) -> None:
        now = self._clock()
        async with self._sessionmaker() as session:
            sources = list((await session.scalars(select(Source).where(Source.active))).all())
            readers = await self._load_readers(session)
        queries = build_queries(readers)
        jobs = build_jobs(
            sources,
            [(q.text, q.locale) for q in queries],
            http=self._http,
            resolver=self._resolver,
            settings=self._settings,
        )
        log.info("ingest_start", sources=len(sources), jobs=len(jobs), queries=len(queries))

        outcomes = await self._fetch_all(jobs, stats)
        await self._record_health(outcomes, stats, now)

        candidates, seen, dup_urls = select_candidates(outcomes, now)
        stats.fetched = seen
        stats.duplicates += dup_urls
        async with self._sessionmaker() as session:
            candidates, known = await self._drop_known_urls(session, candidates)
        stats.duplicates += known
        log.info("ingest_candidates", fetched=seen, candidates=len(candidates))

        t0 = time.monotonic()
        extracted = await self._extract_all(interleave_by_domain(candidates), stats)
        stats.timings["_extract_seconds"] = round(time.monotonic() - t0, 1)

        rows = self._to_rows(extracted, now, stats)
        async with self._sessionmaker() as session:
            rows = await self._drop_known_hashes(session, rows, stats)
            stats.new = await self._insert(session, rows)

    # ---- fetching ----

    async def _fetch_all(self, jobs: Sequence[FetchJob], stats: IngestStats) -> list[JobOutcome]:
        async def one(job: FetchJob) -> JobOutcome:
            t0 = time.monotonic()
            try:
                result = await job.fetcher.fetch()
                error = None
            except Exception as exc:  # one broken source must never stop the others
                result, error = None, f"{type(exc).__name__}: {exc}"
                log.warning("fetch_failed", fetcher=job.fetcher.label, error=error[:200])
            return JobOutcome(job, result, error, time.monotonic() - t0)

        outcomes = await asyncio.gather(*(one(j) for j in jobs))
        for outcome in outcomes:
            stats.timings[outcome.job.fetcher.label] = round(outcome.seconds, 2)
            if outcome.result and outcome.result.skipped:
                stats.dropped += outcome.result.skipped
        return list(outcomes)

    async def _record_health(
        self, outcomes: Sequence[JobOutcome], stats: IngestStats, now: datetime
    ) -> None:
        """Per source: a failure only counts when every one of its fetch jobs failed."""
        by_source: dict[uuid.UUID, list[JobOutcome]] = {}
        for outcome in outcomes:
            if outcome.job.source is not None:
                by_source.setdefault(outcome.job.source.id, []).append(outcome)
        stats.sources_failed = sum(1 for o in outcomes if o.error)
        async with self._sessionmaker() as session:
            for source_id, group in by_source.items():
                source = await session.get(Source, source_id)
                if source is None:
                    continue
                ok = [o for o in group if o.result is not None]
                if ok:
                    first = ok[0].result
                    assert first is not None
                    record_success(source, now, etag=first.etag, last_modified=first.last_modified)
                elif record_failure(source, now):
                    stats.sources_deactivated += 1
                    log.warning("source_deactivated", source=source.name)
            await session.commit()

    # ---- extraction ----

    async def _extract_all(
        self, candidates: Sequence[Candidate], stats: IngestStats
    ) -> list[tuple[Candidate, Extracted | None]]:
        sem = asyncio.Semaphore(EXTRACT_CONCURRENCY)

        async def one(candidate: Candidate) -> tuple[Candidate, Extracted | None]:
            item = candidate.item
            if item.content_text:  # e.g. an arXiv abstract: already the full text
                return candidate, Extracted(text=item.content_text)
            async with sem:
                try:
                    # Fetch the URL as published: the canonical form drops "www.", which many
                    # sites answer with a redirect (or a 403).
                    return candidate, await self._extractor.extract(
                        candidate.item.url, high_value=candidate.high_value
                    )
                except RobotsDisallowedError:
                    stats.drop_reasons[DropReason.ROBOTS] += 1
                except Exception as exc:  # network errors, parser crashes, retries exhausted
                    log.info("extract_failed", url=candidate.url, error=type(exc).__name__)
                    stats.failed += 1
            return candidate, None

        return list(await asyncio.gather(*(one(c) for c in candidates)))

    def _to_rows(
        self,
        extracted: Iterable[tuple[Candidate, Extracted | None]],
        now: datetime,
        stats: IngestStats,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for candidate, page in extracted:
            if page is None:
                continue
            item = candidate.item
            words = word_count(page.text)
            published = item.published_at or page.published_at
            reason = drop_reason(
                published_at=published,
                word_count=words,
                language=page.language,
                allowed_languages=self._settings.allowed_languages,
                now=now,
            )
            if reason is not None:
                stats.drop_reasons[reason] += 1
                continue
            title = item.title or page.title or ""
            rows.append(
                {
                    "source_id": candidate.source_id,
                    "url": candidate.url,
                    "title": title,
                    "author": item.author or page.author,
                    "published_at": published or now,
                    "fetched_at": now,
                    "language": page.language,
                    "image_url": item.image_url or page.image_url,
                    "excerpt": make_excerpt(page.text),
                    "content_text": page.text,
                    "content_hash": content_hash(title, page.text),
                    "word_count": words,
                }
            )
        stats.dropped += sum(stats.drop_reasons.values())
        return rows

    # ---- persistence ----

    async def _drop_known_urls(
        self, session: AsyncSession, candidates: list[Candidate]
    ) -> tuple[list[Candidate], int]:
        if not candidates:
            return [], 0
        known: set[str] = set()
        urls = [c.url for c in candidates]
        for i in range(0, len(urls), 500):
            rows = await session.scalars(
                select(Article.url).where(Article.url.in_(urls[i : i + 500]))
            )
            known.update(rows)
        fresh = [c for c in candidates if c.url not in known]
        return fresh, len(candidates) - len(fresh)

    async def _drop_known_hashes(
        self, session: AsyncSession, rows: list[dict[str, Any]], stats: IngestStats
    ) -> list[dict[str, Any]]:
        hashes = [r["content_hash"] for r in rows]
        known: set[str] = set()
        for i in range(0, len(hashes), 500):
            found = await session.scalars(
                select(Article.content_hash).where(Article.content_hash.in_(hashes[i : i + 500]))
            )
            known.update(h for h in found if h)
        kept: list[dict[str, Any]] = []
        for row in rows:
            if row["content_hash"] in known:
                stats.duplicates += 1
                continue
            known.add(row["content_hash"])  # also dedupes within this batch
            kept.append(row)
        return kept

    async def _insert(self, session: AsyncSession, rows: list[dict[str, Any]]) -> int:
        inserted = 0
        for i in range(0, len(rows), INSERT_CHUNK):
            stmt = (
                insert(Article)
                .values(rows[i : i + INSERT_CHUNK])
                .on_conflict_do_nothing(index_elements=["url"])
                .returning(Article.id)
            )
            inserted += len((await session.execute(stmt)).all())
        await session.commit()
        return inserted

    @staticmethod
    async def _load_readers(session: AsyncSession) -> list[ReaderInterests]:
        rows = await session.execute(
            select(ReaderProfile.keywords, ReaderProfile.entities, User.timezone).join(
                User, User.id == ReaderProfile.user_id
            )
        )
        return [ReaderInterests(list(k), dict(e), tz) for k, e, tz in rows.tuples()]

    # ---- run bookkeeping ----

    async def _start_run(self) -> uuid.UUID:
        async with self._sessionmaker() as session:
            run = PipelineRun(stage="ingest", status=RunStatus.RUNNING, stats={})
            session.add(run)
            await session.commit()
            return run.id

    async def _finish_run(
        self, run_id: uuid.UUID, status: RunStatus, stats: IngestStats, seconds: float
    ) -> None:
        async with self._sessionmaker() as session:
            run = await session.get(PipelineRun, run_id)
            if run is None:
                return
            run.status = status
            run.finished_at = self._clock()
            run.stats = {**stats.as_dict(), "total_seconds": round(seconds, 1)}
            await session.commit()
