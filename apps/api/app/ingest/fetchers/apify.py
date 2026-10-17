"""Apify adapter: run an actor, read its dataset, map items to RawItem.

Used only as a fallback and only when APIFY_TOKEN is set (see Settings.apify_enabled). Tests
inject a fake ActorRunner; nothing here talks to Apify without a token.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol

import structlog
from apify_client import ApifyClientAsync

from app.ingest.fetchers.base import FetchError
from app.ingest.types import Extracted, FetchResult, RawItem

log = structlog.get_logger(__name__)

MAX_RUN_COST_USD = Decimal("0.50")

_URL_KEYS = ("url", "link", "articleUrl", "sourceUrl", "decodedUrl")
_TITLE_KEYS = ("title", "headline")
_DATE_KEYS = ("publishedAt", "datePublished", "published", "date")
_TEXT_KEYS = ("text", "content", "markdown", "body")
_INPUT_URL_KEYS = ("inputUrl", "googleUrl", "originalUrl", "input", "sourceLink")


class ActorRunner(Protocol):
    async def run_actor(self, actor_id: str, run_input: dict[str, Any]) -> list[dict[str, Any]]: ...


class ApifyActorRunner:
    """Runs an actor to completion with a spend cap and returns its dataset items."""

    def __init__(self, token: str, max_cost_usd: Decimal = MAX_RUN_COST_USD) -> None:
        self._client = ApifyClientAsync(token)
        self._max_cost = max_cost_usd

    async def run_actor(self, actor_id: str, run_input: dict[str, Any]) -> list[dict[str, Any]]:
        run = await self._client.actor(actor_id).call(
            run_input=run_input, max_total_charge_usd=self._max_cost
        )
        dataset_id = getattr(run, "default_dataset_id", None)
        if run is None or not dataset_id:
            raise FetchError(f"Apify actor {actor_id} produced no dataset")
        page = await self._client.dataset(dataset_id).list_items()
        return [item for item in page.items if isinstance(item, dict)]


def _first(item: dict[str, Any], keys: Sequence[str]) -> Any | None:
    return next((item[k] for k in keys if item.get(k)), None)


def _parse_date(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def map_item(item: dict[str, Any], origin: str) -> RawItem | None:
    url, title = _first(item, _URL_KEYS), _first(item, _TITLE_KEYS)
    if not url or not title:
        return None
    return RawItem(
        url=str(url),
        title=str(title),
        published_at=_parse_date(_first(item, _DATE_KEYS)),
        author=item.get("author") if isinstance(item.get("author"), str) else None,
        image_url=item.get("image") or item.get("imageUrl"),
        content_text=_first(item, _TEXT_KEYS),
        origin=origin,
    )


class ApifyFetcher:
    """Generic: any actor whose dataset items look like articles."""

    def __init__(
        self, runner: ActorRunner, actor_id: str, run_input: dict[str, Any], label: str
    ) -> None:
        self._runner = runner
        self._actor_id = actor_id
        self._input = run_input
        self.label = label

    async def fetch(self) -> FetchResult:
        raw = await self._runner.run_actor(self._actor_id, self._input)
        mapped = [map_item(i, self.label) for i in raw]
        items = [i for i in mapped if i is not None]
        return FetchResult(items=items, skipped=len(raw) - len(items))


class ApifyLinkDecoder:
    """Google News link decoding through hiver/google-news-scraper (or APIFY_GNEWS_ACTOR)."""

    def __init__(self, runner: ActorRunner, actor_id: str) -> None:
        self._runner = runner
        self._actor_id = actor_id

    async def decode(self, urls: Sequence[str]) -> dict[str, str | None]:
        result: dict[str, str | None] = dict.fromkeys(urls)
        if not urls:
            return result
        try:
            rows = await self._runner.run_actor(self._actor_id, {"urls": list(urls)})
        except Exception as exc:  # fallback path: never take the whole source down with it
            log.warning("apify_decode_failed", error=type(exc).__name__)
            return result
        for row in rows:
            source = _first(row, _INPUT_URL_KEYS)
            decoded = _first(row, ("decodedUrl", "publisherUrl", "url"))
            if source in result and decoded and "news.google.com" not in str(decoded):
                result[str(source)] = str(decoded)
        return result


class ApifyPageExtractor:
    """Last-resort full-text extraction (apify/website-content-crawler) for high-value sources."""

    def __init__(self, runner: ActorRunner, actor_id: str) -> None:
        self._runner = runner
        self._actor_id = actor_id

    async def extract(self, url: str) -> Extracted | None:
        try:
            rows = await self._runner.run_actor(
                self._actor_id, {"startUrls": [{"url": url}], "maxCrawlPages": 1}
            )
        except Exception as exc:
            log.warning("apify_extract_failed", error=type(exc).__name__)
            return None
        for row in rows:
            text = _first(row, _TEXT_KEYS)
            if text:
                raw_meta = row.get("metadata")
                metadata: dict[str, Any] = raw_meta if isinstance(raw_meta, dict) else {}
                return Extracted(
                    text=str(text),
                    title=metadata.get("title") or row.get("title"),
                    language=metadata.get("languageCode"),
                )
        return None
