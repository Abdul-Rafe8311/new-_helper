import pytest

from app.ingest.urls import canonicalize_url, domain_of


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://www.Example.com/a/b/?utm_source=x&utm_medium=y", "https://example.com/a/b"),
        ("https://example.com/story?id=7&fbclid=abc&gclid=def", "https://example.com/story?id=7"),
        ("https://example.com/story/#comments", "https://example.com/story"),
        ("https://example.com/news/story/amp/", "https://example.com/news/story"),
        ("https://example.com/news/story?amp=1", "https://example.com/news/story"),
        ("https://amp.example.com/news/story", "https://example.com/news/story"),
        ("https://example.com//a///b", "https://example.com/a/b"),
        ("https://example.com/s?b=2&a=1", "https://example.com/s?a=1&b=2"),
        ("  https://example.com/x  ", "https://example.com/x"),
        ("https://example.com:8443/x/", "https://example.com:8443/x"),
        ("https://example.com/campaign", "https://example.com/campaign"),
    ],
)
def test_canonicalize_url(raw: str, expected: str) -> None:
    assert canonicalize_url(raw) == expected


def test_canonical_form_is_idempotent() -> None:
    once = canonicalize_url("https://WWW.example.com/a/amp/?utm_x=1&z=1")
    assert canonicalize_url(once) == once


def test_domain_of_strips_www() -> None:
    assert domain_of("https://www.bbc.co.uk/news/1") == "bbc.co.uk"
