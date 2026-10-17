from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import respx
from tenacity import wait_none

from app.ingest.fetchers.base import FetchError
from app.ingest.fetchers.rss import RssFetcher
from app.ingest.http import PoliteClient

FIXTURES = Path(__file__).parent / "fixtures"
URL = "https://wire.example.com/feed.xml"


def _http() -> PoliteClient:
    return PoliteClient("NewsHelperBot/0.1", wait=wait_none())


@respx.mock
async def test_parses_entries_and_keeps_validators() -> None:
    respx.get(URL).mock(
        return_value=httpx.Response(
            200,
            content=(FIXTURES / "feed_basic.xml").read_bytes(),
            headers={"etag": '"v1"', "last-modified": "Fri, 17 Oct 2026 07:00:00 GMT"},
        )
    )
    async with _http() as http:
        result = await RssFetcher(http, URL, "Example Wire").fetch()
    assert result.etag == '"v1"'
    assert result.last_modified == "Fri, 17 Oct 2026 07:00:00 GMT"
    assert [i.title for i in result.items] == [
        "Central bank holds rates & signals patience",
        "Floods displace thousands in the south",
    ]
    first = result.items[0]
    assert first.published_at == datetime(2026, 10, 17, 6, 30, tzinfo=UTC)
    assert first.author == "Ayesha Khan"
    assert first.summary == "The bank left its policy rate unchanged on Friday."
    assert first.image_url == "https://wire.example.com/img/rates.jpg"
    assert first.origin == "Example Wire"


@respx.mock
async def test_conditional_get_sends_validators_and_handles_304() -> None:
    route = respx.get(URL).mock(return_value=httpx.Response(304))
    async with _http() as http:
        fetcher = RssFetcher(
            http, URL, "x", etag='"v1"', last_modified="Fri, 17 Oct 2026 07:00:00 GMT"
        )
        result = await fetcher.fetch()
    sent = route.calls.last.request.headers
    assert sent["if-none-match"] == '"v1"'
    assert sent["if-modified-since"] == "Fri, 17 Oct 2026 07:00:00 GMT"
    assert result.not_modified
    assert result.items == []
    assert result.etag == '"v1"'


@respx.mock
async def test_http_error_raises_fetch_error() -> None:
    respx.get(URL).mock(return_value=httpx.Response(404))
    async with _http() as http:
        with pytest.raises(FetchError, match="404"):
            await RssFetcher(http, URL, "x").fetch()


@respx.mock
async def test_garbage_body_raises_fetch_error() -> None:
    respx.get(URL).mock(return_value=httpx.Response(200, content=b"<html><body>nope"))
    async with _http() as http:
        with pytest.raises(FetchError):
            await RssFetcher(http, URL, "x").fetch()


@respx.mock
async def test_feed_body_is_used_as_content_only_when_it_is_the_full_article() -> None:
    respx.get(URL).mock(
        return_value=httpx.Response(200, content=(FIXTURES / "feed_full_content.xml").read_bytes())
    )
    async with _http() as http:
        result = await RssFetcher(http, URL, "Full Content Wire").fetch()
    full, teaser = result.items
    assert full.content_text is not None
    assert len(full.content_text.split()) >= 200
    assert "<p>" not in full.content_text
    assert teaser.content_text is None
