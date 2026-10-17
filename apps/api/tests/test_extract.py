from pathlib import Path

import httpx
import pytest
import respx
from tenacity import wait_none

from app.ingest.extract import (
    ArticleExtractor,
    detect_language,
    make_excerpt,
    newspaper_backend,
    trafilatura_backend,
    word_count,
)
from app.ingest.http import PoliteClient, RobotsDisallowedError
from app.ingest.types import Extracted

FIX = Path(__file__).parent / "fixtures"
URL = "https://wire.example.com/story"
FULL = (FIX / "article_full.html").read_text()
SHORT = (FIX / "article_short.html").read_text()


def _http() -> PoliteClient:
    return PoliteClient("NewsHelperBot/0.1", wait=wait_none())


@pytest.fixture(autouse=True)
def _no_robots_file() -> None:
    """Pages are fetched with robots.txt respected; by default the site has none."""
    respx.get("https://wire.example.com/robots.txt").mock(return_value=httpx.Response(404))


def _words(n: int) -> Extracted:
    return Extracted(text=" ".join(["word"] * n))


class FakeApify:
    def __init__(self, result: Extracted | None) -> None:
        self.result = result
        self.calls: list[str] = []

    async def extract(self, url: str) -> Extracted | None:
        self.calls.append(url)
        return self.result


def test_excerpt_cuts_on_a_word_boundary() -> None:
    text = "alpha " * 200
    excerpt = make_excerpt(text)
    assert len(excerpt) <= 301
    assert excerpt.endswith("…")
    assert make_excerpt("short text") == "short text"


def test_detect_language() -> None:
    assert (
        detect_language("The finance ministry said on Friday that revenue rose sharply. " * 5)
        == "en"
    )
    assert detect_language("too short") is None


def test_trafilatura_reads_the_lead_image() -> None:
    result = trafilatura_backend(FULL, URL)
    assert result is not None
    assert result.image_url == "https://wire.example.com/img/revenue.jpg"


def test_real_backends_extract_the_fixture() -> None:
    for backend in (trafilatura_backend, newspaper_backend):
        result = backend(FULL, URL)
        assert result is not None
        assert word_count(result.text) >= 120
        assert "finance ministry" in result.text
        assert "Copyright" not in result.text
        assert result.author == "Ayesha Khan"
        assert result.published_at is not None
        assert result.published_at.date().isoformat() == "2026-10-17"


@respx.mock
async def test_first_backend_wins_when_long_enough() -> None:
    respx.get(URL).mock(return_value=httpx.Response(200, text="<html></html>"))
    calls: list[str] = []

    def first(html: str, url: str) -> Extracted | None:
        calls.append("first")
        return _words(200)

    def second(html: str, url: str) -> Extracted | None:
        calls.append("second")
        return _words(300)

    async with _http() as http:
        result = await ArticleExtractor(http, backends=[first, second]).extract(URL)
    assert calls == ["first"]
    assert result is not None
    assert word_count(result.text) == 200


@respx.mock
async def test_falls_back_to_next_backend_when_short_and_keeps_longest() -> None:
    respx.get(URL).mock(return_value=httpx.Response(200, text="<html></html>"))
    calls: list[str] = []

    def first(html: str, url: str) -> Extracted | None:
        calls.append("first")
        return _words(40)

    def broken(html: str, url: str) -> Extracted | None:
        calls.append("broken")
        raise ValueError("parser crashed")

    def third(html: str, url: str) -> Extracted | None:
        calls.append("third")
        return _words(150)

    async with _http() as http:
        result = await ArticleExtractor(http, backends=[first, broken, third]).extract(URL)
    assert calls == ["first", "broken", "third"]
    assert result is not None
    assert word_count(result.text) == 150


@respx.mock
async def test_apify_only_for_high_value_sources_when_backends_fall_short() -> None:
    respx.get(URL).mock(return_value=httpx.Response(200, text=SHORT))
    apify = FakeApify(_words(500))
    async with _http() as http:
        extractor = ArticleExtractor(http, apify=apify)
        normal = await extractor.extract(URL, high_value=False)
        assert apify.calls == []
        assert normal is not None
        assert word_count(normal.text) < 120
        valuable = await extractor.extract(URL, high_value=True)
    assert apify.calls == [URL]
    assert valuable is not None
    assert word_count(valuable.text) == 500


@respx.mock
async def test_apify_not_called_when_open_source_succeeds() -> None:
    respx.get(URL).mock(return_value=httpx.Response(200, text=FULL))
    apify = FakeApify(_words(500))
    async with _http() as http:
        result = await ArticleExtractor(http, apify=apify).extract(URL, high_value=True)
    assert apify.calls == []
    assert result is not None
    assert result.language == "en"


@respx.mock
async def test_apify_rescues_pages_that_return_http_errors() -> None:
    respx.get(URL).mock(return_value=httpx.Response(403))
    apify = FakeApify(_words(200))
    async with _http() as http:
        result = await ArticleExtractor(http, apify=apify).extract(URL, high_value=True)
    assert result is not None
    assert word_count(result.text) == 200


@respx.mock
async def test_no_apify_and_nothing_extracted_returns_none() -> None:
    respx.get(URL).mock(return_value=httpx.Response(404))
    async with _http() as http:
        assert await ArticleExtractor(http).extract(URL, high_value=True) is None


@respx.mock
async def test_robots_disallow_stops_extraction() -> None:
    respx.get("https://wire.example.com/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow: /\n")
    )
    page = respx.get(URL).mock(return_value=httpx.Response(200, text=FULL))
    async with _http() as http:
        with pytest.raises(RobotsDisallowedError):
            await ArticleExtractor(http).extract(URL)
    assert page.call_count == 0
