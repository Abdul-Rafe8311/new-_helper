"""Google News RSS search feeds.

The feed carries headlines and timestamps but no article body, and its links are encoded
redirects. Each link is decoded to the publisher URL (cached in `decoded_links`); failures are
skipped. If too many fail and a fallback decoder (Apify) is configured, the rest go there.
Only /rss/search is used, never the HTML search page.
"""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Protocol

import feedparser
import structlog
from googlenewsdecoder import gnews_decoder_async

from app.ingest.fetchers.base import FetchError, strip_html, struct_to_datetime
from app.ingest.http import PoliteClient
from app.ingest.types import FetchResult, RawItem

log = structlog.get_logger(__name__)

SEARCH_URL = "https://news.google.com/rss/search"
FALLBACK_FAILURE_RATE = 0.3
DECODE_CONCURRENCY = 4


@dataclass(frozen=True)
class Locale:
    hl: str
    gl: str
    ceid: str


US = Locale("en-US", "US", "US:en")
PAKISTAN = Locale("en-PK", "PK", "PK:en")


class LinkDecoder(Protocol):
    async def decode(self, urls: Sequence[str]) -> dict[str, str | None]:
        """Map each Google News link to its publisher URL, or None when it cannot be decoded."""
        ...


class LinkCache(Protocol):
    async def get_many(self, urls: Sequence[str]) -> dict[str, str]: ...

    async def put_many(self, mapping: dict[str, str]) -> None: ...


class GoogleNewsDecoder:
    """googlenewsdecoder's async API, a few links at a time to stay under Google's limits."""

    def __init__(self, concurrency: int = DECODE_CONCURRENCY, timeout: float = 10.0) -> None:
        self._sem = asyncio.Semaphore(concurrency)
        self._timeout = timeout

    async def _one(self, url: str) -> str | None:
        async with self._sem:
            try:
                result = await gnews_decoder_async(url, timeout=self._timeout)
            except Exception as exc:  # the library raises broadly on rate limits and bad pages
                log.info("gnews_decode_error", error=type(exc).__name__)
                return None
        decoded = result.get("decoded_url") if isinstance(result, dict) else None
        return str(decoded) if result.get("status") and decoded else None

    async def decode(self, urls: Sequence[str]) -> dict[str, str | None]:
        results = await asyncio.gather(*(self._one(u) for u in urls))
        return dict(zip(urls, results, strict=True))


class LinkResolver:
    """Cache -> primary decoder -> (when failures exceed the threshold) fallback decoder."""

    def __init__(
        self,
        cache: LinkCache,
        primary: LinkDecoder,
        fallback: LinkDecoder | None = None,
        failure_threshold: float = FALLBACK_FAILURE_RATE,
    ) -> None:
        self._cache = cache
        self._primary = primary
        self._fallback = fallback
        self._threshold = failure_threshold

    async def resolve(self, urls: Sequence[str]) -> dict[str, str | None]:
        unique = list(dict.fromkeys(urls))
        resolved: dict[str, str | None] = dict(await self._cache.get_many(unique))
        todo = [u for u in unique if u not in resolved]
        if todo:
            fresh = await self._primary.decode(todo)
            failed = [u for u, v in fresh.items() if not v]
            if self._fallback and len(failed) / len(todo) > self._threshold:
                log.info("gnews_fallback_decode", failed=len(failed), total=len(todo))
                fresh.update(await self._fallback.decode(failed))
            await self._cache.put_many({u: v for u, v in fresh.items() if v})
            resolved.update(fresh)
        return {u: resolved.get(u) for u in unique}


class GoogleNewsFetcher:
    def __init__(
        self,
        http: PoliteClient,
        resolver: LinkResolver,
        query: str,
        locale: Locale = US,
    ) -> None:
        self._http = http
        self._resolver = resolver
        self._query = query
        self._locale = locale
        self.label = f"google_news:{locale.gl}:{query}"

    async def fetch(self) -> FetchResult:
        response = await self._http.get(
            SEARCH_URL,
            params={
                "q": f"{self._query} when:1d",
                "hl": self._locale.hl,
                "gl": self._locale.gl,
                "ceid": self._locale.ceid,
            },
        )
        if response.status_code >= 400:
            raise FetchError(f"Google News returned HTTP {response.status_code}")
        parsed = feedparser.parse(response.content)
        if parsed.bozo and not parsed.entries:
            raise FetchError(f"unparseable Google News feed: {parsed.bozo_exception}")
        candidates = [self._to_item(entry) for entry in parsed.entries]
        items = [i for i in candidates if i is not None]
        decoded = await self._resolver.resolve([i.url for i in items])
        resolved = [replace(i, url=publisher) for i in items if (publisher := decoded.get(i.url))]
        return FetchResult(items=resolved, skipped=len(items) - len(resolved))

    def _to_item(self, entry: feedparser.FeedParserDict) -> RawItem | None:
        link, title = entry.get("link"), strip_html(entry.get("title"))
        if not link or not title:
            return None
        publisher = (entry.get("source") or {}).get("title")
        suffix = f" - {publisher}"
        if publisher and title.endswith(suffix):
            title = title[: -len(suffix)]
        return RawItem(
            url=link,
            title=title,
            published_at=struct_to_datetime(entry.get("published_parsed")),
            author=publisher,
            origin=self.label,
        )
