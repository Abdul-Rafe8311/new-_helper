"""RSS/Atom feeds via httpx + feedparser, with conditional GET."""

from typing import Any

import feedparser
import structlog

from app.ingest.fetchers.base import FetchError, strip_html, struct_to_datetime
from app.ingest.http import PoliteClient
from app.ingest.types import FetchResult, RawItem

log = structlog.get_logger(__name__)


def entry_image(entry: Any) -> str | None:
    for key in ("media_content", "media_thumbnail"):
        for media in entry.get(key) or []:
            if url := media.get("url"):
                return str(url)
    for link in entry.get("links") or []:
        if link.get("rel") == "enclosure" and str(link.get("type", "")).startswith("image/"):
            return str(link["href"])
    return None


def parse_entries(content: bytes, origin: str) -> list[RawItem]:
    parsed = feedparser.parse(content)
    if parsed.bozo and not parsed.entries:
        raise FetchError(f"unparseable feed: {parsed.bozo_exception}")
    items: list[RawItem] = []
    for entry in parsed.entries:
        link, title = entry.get("link"), strip_html(entry.get("title"))
        if not link or not title:
            continue
        items.append(
            RawItem(
                url=link,
                title=title,
                published_at=struct_to_datetime(
                    entry.get("published_parsed") or entry.get("updated_parsed")
                ),
                summary=strip_html(entry.get("summary")),
                author=entry.get("author"),
                image_url=entry_image(entry),
                origin=origin,
            )
        )
    return items


class RssFetcher:
    def __init__(
        self,
        http: PoliteClient,
        url: str,
        label: str,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> None:
        self._http = http
        self._url = url
        self.label = label
        self._etag = etag
        self._last_modified = last_modified

    async def fetch(self) -> FetchResult:
        headers: dict[str, str] = {}
        if self._etag:
            headers["If-None-Match"] = self._etag
        if self._last_modified:
            headers["If-Modified-Since"] = self._last_modified
        response = await self._http.get(self._url, headers=headers)
        if response.status_code == 304:
            return FetchResult(
                etag=self._etag, last_modified=self._last_modified, not_modified=True
            )
        if response.status_code >= 400:
            raise FetchError(f"{self._url} returned HTTP {response.status_code}")
        return FetchResult(
            items=parse_entries(response.content, self.label),
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
        )
