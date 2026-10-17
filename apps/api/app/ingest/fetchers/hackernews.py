"""Hacker News via the Algolia API: the front page plus the top stories of the last 24h."""

import time
from collections.abc import Callable
from typing import Any

from app.ingest.fetchers.base import FetchError, epoch_to_datetime
from app.ingest.http import PoliteClient
from app.ingest.types import FetchResult, RawItem

BASE_URL = "https://hn.algolia.com/api/v1/search"
MIN_POINTS = 40


class HackerNewsFetcher:
    label = "hackernews"

    def __init__(
        self,
        http: PoliteClient,
        *,
        min_points: int = MIN_POINTS,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._http = http
        self._min_points = min_points
        self._clock = clock

    async def _hits(self, params: dict[str, str]) -> list[dict[str, Any]]:
        response = await self._http.get(BASE_URL, params=params)
        if response.status_code >= 400:
            raise FetchError(f"HN Algolia returned HTTP {response.status_code}")
        hits = response.json().get("hits", [])
        return [h for h in hits if isinstance(h, dict)]

    async def fetch(self) -> FetchResult:
        since = int(self._clock()) - 24 * 3600
        front = await self._hits({"tags": "front_page", "hitsPerPage": "60"})
        top = await self._hits(
            {
                "tags": "story",
                "numericFilters": f"created_at_i>{since},points>{self._min_points}",
                "hitsPerPage": "100",
            }
        )
        seen: set[str] = set()
        items: list[RawItem] = []
        skipped = 0
        for hit in [*front, *top]:
            url, title = hit.get("url"), hit.get("title")
            if not url or not title:  # Ask HN / text posts have no external article
                skipped += 1
                continue
            if url in seen:
                continue
            seen.add(url)
            items.append(
                RawItem(
                    url=url,
                    title=title,
                    published_at=epoch_to_datetime(hit.get("created_at_i")),
                    author=hit.get("author"),
                    origin=self.label,
                )
            )
        return FetchResult(items=items, skipped=skipped)
