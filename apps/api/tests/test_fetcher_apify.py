from typing import Any

from app.ingest.fetchers.apify import (
    ApifyFetcher,
    ApifyLinkDecoder,
    ApifyPageExtractor,
    map_item,
)

G1 = "https://news.google.com/rss/articles/AAA"
G2 = "https://news.google.com/rss/articles/BBB"


class FakeRunner:
    def __init__(self, rows: list[dict[str, Any]] | Exception) -> None:
        self.rows = rows
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def run_actor(self, actor_id: str, run_input: dict[str, Any]) -> list[dict[str, Any]]:
        self.calls.append((actor_id, run_input))
        if isinstance(self.rows, Exception):
            raise self.rows
        return self.rows


def test_map_item_tolerates_field_aliases() -> None:
    item = map_item(
        {
            "link": "https://p.test/a",
            "headline": "Hello",
            "datePublished": "2026-10-17T05:00:00Z",
            "author": "Sam",
            "imageUrl": "https://p.test/i.jpg",
            "content": "body",
        },
        "apify:test",
    )
    assert item is not None
    assert (item.url, item.title, item.author) == ("https://p.test/a", "Hello", "Sam")
    assert item.published_at is not None
    assert item.published_at.hour == 5
    assert item.content_text == "body"
    assert map_item({"title": "no url"}, "x") is None


async def test_fetcher_maps_dataset_items() -> None:
    runner = FakeRunner([{"url": "https://p.test/a", "title": "A"}, {"title": "broken"}])
    result = await ApifyFetcher(runner, "some/actor", {"q": 1}, "apify:x").fetch()
    assert [i.url for i in result.items] == ["https://p.test/a"]
    assert result.skipped == 1
    assert runner.calls == [("some/actor", {"q": 1})]


async def test_link_decoder_maps_results_back_to_inputs() -> None:
    runner = FakeRunner(
        [
            {"inputUrl": G1, "decodedUrl": "https://p.test/a"},
            {"inputUrl": G2, "decodedUrl": "https://news.google.com/still-google"},
        ]
    )
    out = await ApifyLinkDecoder(runner, "hiver/google-news-scraper").decode([G1, G2])
    assert out == {G1: "https://p.test/a", G2: None}


async def test_link_decoder_swallows_actor_errors() -> None:
    out = await ApifyLinkDecoder(FakeRunner(RuntimeError("boom")), "a/b").decode([G1])
    assert out == {G1: None}


async def test_page_extractor_returns_text_or_none() -> None:
    ok = FakeRunner([{"text": "full article", "metadata": {"title": "T", "languageCode": "en"}}])
    got = await ApifyPageExtractor(ok, "apify/website-content-crawler").extract("https://p.test")
    assert got is not None
    assert (got.text, got.language) == ("full article", "en")
    assert await ApifyPageExtractor(FakeRunner([]), "a/b").extract("https://p.test") is None
    assert await ApifyPageExtractor(FakeRunner(ValueError()), "a/b").extract("https://p") is None
