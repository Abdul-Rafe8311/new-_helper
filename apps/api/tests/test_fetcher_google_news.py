from collections.abc import Sequence
from pathlib import Path

import httpx
import pytest
import respx
from tenacity import wait_none

from app.ingest.fetchers import google_news
from app.ingest.fetchers.base import FetchError
from app.ingest.fetchers.google_news import (
    PAKISTAN,
    GoogleNewsDecoder,
    GoogleNewsFetcher,
    LinkResolver,
)
from app.ingest.http import PoliteClient

FEED = (Path(__file__).parent / "fixtures" / "google_news.xml").read_bytes()
L1 = "https://news.google.com/rss/articles/CBMiAAAA1?oc=5"
L2 = "https://news.google.com/rss/articles/CBMiAAAA2?oc=5"
L3 = "https://news.google.com/rss/articles/CBMiAAAA3?oc=5"


class MemoryCache:
    def __init__(self, seed: dict[str, str] | None = None) -> None:
        self.data = dict(seed or {})

    async def get_many(self, urls: Sequence[str]) -> dict[str, str]:
        return {u: self.data[u] for u in urls if u in self.data}

    async def put_many(self, mapping: dict[str, str]) -> None:
        self.data.update(mapping)


class FakeDecoder:
    def __init__(self, table: dict[str, str | None]) -> None:
        self.table = table
        self.calls: list[list[str]] = []

    async def decode(self, urls: Sequence[str]) -> dict[str, str | None]:
        self.calls.append(list(urls))
        return {u: self.table.get(u) for u in urls}


def _http() -> PoliteClient:
    return PoliteClient("NewsHelperBot/0.1", wait=wait_none())


def _feed_route() -> respx.Route:
    return respx.get("https://news.google.com/rss/search").mock(
        return_value=httpx.Response(200, content=FEED)
    )


@respx.mock
async def test_builds_search_request_and_decodes_links() -> None:
    route = _feed_route()
    decoder = FakeDecoder(
        {L1: "https://dawn.com/a", L2: "https://thenews.com.pk/b", L3: "https://geo.tv/c"}
    )
    resolver = LinkResolver(MemoryCache(), decoder)
    async with _http() as http:
        result = await GoogleNewsFetcher(http, resolver, "lahore qalandars", PAKISTAN).fetch()
    params = route.calls.last.request.url.params
    assert params["q"] == "lahore qalandars when:1d"
    assert (params["hl"], params["gl"], params["ceid"]) == ("en-PK", "PK", "PK:en")
    assert [i.url for i in result.items] == [
        "https://dawn.com/a",
        "https://thenews.com.pk/b",
        "https://geo.tv/c",
    ]
    assert result.items[0].title == "Qalandars sign overseas star for PSL"
    assert result.items[0].author == "Dawn"
    assert result.skipped == 0


@respx.mock
async def test_undecodable_links_are_skipped() -> None:
    _feed_route()
    decoder = FakeDecoder({L1: "https://dawn.com/a", L2: None, L3: None})
    resolver = LinkResolver(MemoryCache(), decoder)
    async with _http() as http:
        result = await GoogleNewsFetcher(http, resolver, "q").fetch()
    assert [i.url for i in result.items] == ["https://dawn.com/a"]
    assert result.skipped == 2


@respx.mock
async def test_cached_links_are_not_decoded_again() -> None:
    _feed_route()
    cache = MemoryCache({L1: "https://dawn.com/a", L2: "https://thenews.com.pk/b"})
    decoder = FakeDecoder({L3: "https://geo.tv/c"})
    async with _http() as http:
        result = await GoogleNewsFetcher(http, LinkResolver(cache, decoder), "q").fetch()
    assert decoder.calls == [[L3]]
    assert len(result.items) == 3
    assert cache.data[L3] == "https://geo.tv/c"


async def test_fallback_decoder_used_above_failure_threshold() -> None:
    primary = FakeDecoder({L1: "https://dawn.com/a", L2: None, L3: None})
    fallback = FakeDecoder({L2: "https://thenews.com.pk/b", L3: None})
    resolver = LinkResolver(MemoryCache(), primary, fallback)
    out = await resolver.resolve([L1, L2, L3])
    assert fallback.calls == [[L2, L3]]
    assert out == {L1: "https://dawn.com/a", L2: "https://thenews.com.pk/b", L3: None}


async def test_fallback_not_used_at_or_below_threshold() -> None:
    urls = [f"https://news.google.com/rss/articles/{i}" for i in range(10)]
    table: dict[str, str | None] = {u: f"https://p.test/{i}" for i, u in enumerate(urls)}
    for u in urls[:3]:  # exactly 30% failing: not "more than 30%"
        table[u] = None
    fallback = FakeDecoder({})
    resolver = LinkResolver(MemoryCache(), FakeDecoder(table), fallback)
    await resolver.resolve(urls)
    assert fallback.calls == []


async def test_no_fallback_configured_just_skips() -> None:
    resolver = LinkResolver(MemoryCache(), FakeDecoder({L1: None}), None)
    assert await resolver.resolve([L1]) == {L1: None}


@respx.mock
async def test_http_error_raises_fetch_error() -> None:
    respx.get("https://news.google.com/rss/search").mock(return_value=httpx.Response(403))
    async with _http() as http:
        fetcher = GoogleNewsFetcher(http, LinkResolver(MemoryCache(), FakeDecoder({})), "q")
        with pytest.raises(FetchError, match="403"):
            await fetcher.fetch()


async def test_decoder_reads_the_librarys_success_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake(url: str, **kwargs: object) -> dict[str, object]:
        if url == L1:
            return {"success": True, "decoded_url": "https://dawn.com/a"}
        if url == L2:
            return {"success": False, "message": "rate limited"}
        raise RuntimeError("boom")

    monkeypatch.setattr(google_news, "gnews_decoder_async", fake)
    out = await GoogleNewsDecoder().decode([L1, L2, L3])
    assert out == {L1: "https://dawn.com/a", L2: None, L3: None}


@respx.mock
async def test_only_the_newest_items_are_decoded() -> None:
    _feed_route()
    decoder = FakeDecoder({L1: "https://dawn.com/a", L2: "https://thenews.com.pk/b"})
    async with _http() as http:
        fetcher = GoogleNewsFetcher(http, LinkResolver(MemoryCache(), decoder), "q", max_items=2)
        result = await fetcher.fetch()
    assert decoder.calls == [[L1, L2]]
    assert len(result.items) == 2
