"""arXiv API: newest submissions in one category. Abstracts are the content (no page fetch)."""

import asyncio
import re
import time
from collections.abc import Awaitable, Callable

import feedparser

from app.ingest.fetchers.base import FetchError, struct_to_datetime
from app.ingest.http import PoliteClient
from app.ingest.types import FetchResult, RawItem

API_URL = "https://export.arxiv.org/api/query"
MIN_INTERVAL_SECONDS = 3.0  # arXiv asks for at most one request every three seconds
_CATEGORY = re.compile(r"cat:([A-Za-z.\-]+)")
_SPACE = re.compile(r"\s+")


def category_from_url(url: str) -> str:
    match = _CATEGORY.search(url)
    if not match:
        raise ValueError(f"no arXiv category in {url!r}")
    return match.group(1)


class Throttle:
    """Spaces calls at least `interval` seconds apart, shared by every arXiv fetcher in a run."""

    def __init__(
        self,
        interval: float = MIN_INTERVAL_SECONDS,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._interval = interval
        self._sleep = sleep
        self._lock = asyncio.Lock()
        self._last: float | None = None

    async def wait(self) -> None:
        async with self._lock:
            if self._last is not None:
                remaining = self._interval - (time.monotonic() - self._last)
                if remaining > 0:
                    await self._sleep(remaining)
            self._last = time.monotonic()


def _clean(text: str) -> str:
    return _SPACE.sub(" ", text).strip()


class ArxivFetcher:
    def __init__(
        self,
        http: PoliteClient,
        category: str,
        throttle: Throttle,
        max_results: int = 40,
    ) -> None:
        self._http = http
        self._category = category
        self._throttle = throttle
        self._max_results = max_results
        self.label = f"arxiv:{category}"

    async def fetch(self) -> FetchResult:
        await self._throttle.wait()
        response = await self._http.get(
            API_URL,
            params={
                "search_query": f"cat:{self._category}",
                "sortBy": "submittedDate",
                "sortOrder": "descending",
                "start": "0",
                "max_results": str(self._max_results),
            },
        )
        if response.status_code >= 400:
            raise FetchError(f"arXiv returned HTTP {response.status_code}")
        parsed = feedparser.parse(response.content)
        if parsed.bozo and not parsed.entries:
            raise FetchError(f"unparseable arXiv response: {parsed.bozo_exception}")
        items: list[RawItem] = []
        for entry in parsed.entries:
            link, title, abstract = entry.get("link"), entry.get("title"), entry.get("summary")
            if not link or not title or not abstract:
                continue
            authors = [a.get("name", "") for a in entry.get("authors", [])][:3]
            items.append(
                RawItem(
                    url=link,
                    title=_clean(title),
                    published_at=struct_to_datetime(entry.get("published_parsed")),
                    author=", ".join(a for a in authors if a) or None,
                    content_text=_clean(abstract),
                    origin=self.label,
                )
            )
        return FetchResult(items=items)
