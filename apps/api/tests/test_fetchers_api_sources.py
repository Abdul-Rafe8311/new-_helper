import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import respx
from tenacity import wait_none

from app.ingest.fetchers.arxiv import ArxivFetcher, Throttle, category_from_url
from app.ingest.fetchers.base import FetchError
from app.ingest.fetchers.hackernews import HackerNewsFetcher
from app.ingest.fetchers.reddit import RedditFetcher
from app.ingest.http import PoliteClient

FIX = Path(__file__).parent / "fixtures"


def _http() -> PoliteClient:
    return PoliteClient("NewsHelperBot/0.1", wait=wait_none())


def _json(name: str) -> dict[str, object]:
    return json.loads((FIX / name).read_text())


# ---- Hacker News ----


@respx.mock
async def test_hackernews_merges_front_page_and_top_and_dedupes() -> None:
    route = respx.get("https://hn.algolia.com/api/v1/search").mock(
        side_effect=[
            httpx.Response(200, json=_json("hn_front.json")),
            httpx.Response(200, json=_json("hn_top.json")),
        ]
    )
    async with _http() as http:
        result = await HackerNewsFetcher(http, clock=lambda: 1792200000).fetch()
    assert [i.title for i in result.items] == [
        "A new open model beats the benchmarks",
        "Rust 2.0 roadmap published",
    ]
    assert result.skipped == 1  # the Ask HN post has no URL
    first = route.calls[0].request.url.params
    second = route.calls[1].request.url.params
    assert first["tags"] == "front_page"
    assert second["numericFilters"] == f"created_at_i>{1792200000 - 86400},points>40"
    assert result.items[0].published_at == datetime.fromtimestamp(1792200000, tz=UTC)


@respx.mock
async def test_hackernews_error_raises() -> None:
    respx.get("https://hn.algolia.com/api/v1/search").mock(return_value=httpx.Response(404))
    async with _http() as http:
        with pytest.raises(FetchError):
            await HackerNewsFetcher(http).fetch()


# ---- arXiv ----


def test_category_from_url() -> None:
    assert category_from_url("https://export.arxiv.org/api/query?search_query=cat:cs.AI") == "cs.AI"
    with pytest.raises(ValueError, match="category"):
        category_from_url("https://export.arxiv.org/api/query")


@respx.mock
async def test_arxiv_uses_abstract_as_content() -> None:
    route = respx.get("https://export.arxiv.org/api/query").mock(
        return_value=httpx.Response(200, content=(FIX / "arxiv.xml").read_bytes())
    )
    async with _http() as http:
        result = await ArxivFetcher(http, "cs.AI", Throttle(interval=0)).fetch()
    assert route.calls.last.request.url.params["search_query"] == "cat:cs.AI"
    assert len(result.items) == 1  # the entry without an abstract is dropped
    item = result.items[0]
    assert item.title == "Scaling Laws for Sparse Agents"
    assert item.content_text == (
        "We study how agent performance scales with sparse tool use and show consistent gains."
    )
    assert item.author == "A. Researcher, B. Scientist, C. Student"
    assert item.url == "http://arxiv.org/abs/2610.01234v1"


async def test_throttle_spaces_calls() -> None:
    slept: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    throttle = Throttle(interval=3.0, sleep=fake_sleep)
    await throttle.wait()
    await throttle.wait()
    assert len(slept) == 1
    assert 0 < slept[0] <= 3.0


# ---- Reddit ----


@respx.mock
async def test_reddit_keeps_only_external_sfw_links() -> None:
    route = respx.get("https://www.reddit.com/r/worldnews/top.json").mock(
        return_value=httpx.Response(200, json=_json("reddit_top.json"))
    )
    async with _http() as http:
        result = await RedditFetcher(http, "worldnews").fetch()
    assert [i.url for i in result.items] == ["https://news.example.net/transit"]
    assert result.skipped == 3
    assert route.calls.last.request.url.params["t"] == "day"


@respx.mock
@pytest.mark.parametrize("status", [403, 429, 404])
async def test_reddit_tolerates_blocking(status: int) -> None:
    respx.get("https://www.reddit.com/r/worldnews/top.json").mock(
        return_value=httpx.Response(status)
    )
    async with _http() as http:
        result = await RedditFetcher(http, "worldnews").fetch()
    assert result.items == []
