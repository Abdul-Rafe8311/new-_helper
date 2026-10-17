"""Full-text extraction: trafilatura -> newspaper4k -> (Apify, high-value sources only).

The first backend whose text reaches MIN_WORDS wins; otherwise the longest result is kept so the
caller can still drop it for being too short. Extraction is CPU work, so it runs in a thread.
"""

import asyncio
import re
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Protocol

import py3langid
import structlog
import trafilatura
from newspaper import Article
from trafilatura.settings import Document

from app.ingest.http import PoliteClient
from app.ingest.types import Extracted

log = structlog.get_logger(__name__)

MIN_WORDS = 120
EXCERPT_CHARS = 300

Backend = Callable[[str, str], Extracted | None]


class FallbackExtractor(Protocol):
    async def extract(self, url: str) -> Extracted | None:
        """Return the page text and metadata, or None when nothing usable was found."""


def word_count(text: str) -> int:
    return len(text.split())


def make_excerpt(text: str, limit: int = EXCERPT_CHARS) -> str:
    flat = re.sub(r"\s+", " ", text).strip()
    if len(flat) <= limit:
        return flat
    cut = flat[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:.") + "…"


def detect_language(text: str) -> str | None:
    sample = text[:1500]
    if len(sample.split()) < 20:
        return None
    return str(py3langid.classify(sample)[0])


def _parse_date(value: str | datetime | None) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def trafilatura_backend(html: str, url: str) -> Extracted | None:
    doc = trafilatura.bare_extraction(
        html, url=url, with_metadata=True, favor_precision=True, include_comments=False
    )
    if not isinstance(doc, Document) or not doc.text:
        return None
    return Extracted(
        text=doc.text,
        title=doc.title,
        author=doc.author,
        published_at=_parse_date(doc.date),
        image_url=doc.image,
        language=doc.language,
    )


def newspaper_backend(html: str, url: str) -> Extracted | None:
    article = Article(url)
    article.download(input_html=html)
    article.parse()
    if not article.text:
        return None
    return Extracted(
        text=article.text,
        title=article.title or None,
        author=", ".join(article.authors) or None,
        published_at=_parse_date(article.publish_date),
        image_url=article.top_image or None,
        language=article.meta_lang or None,
    )


DEFAULT_BACKENDS: tuple[Backend, ...] = (trafilatura_backend, newspaper_backend)


class ArticleExtractor:
    def __init__(
        self,
        http: PoliteClient,
        apify: FallbackExtractor | None = None,
        backends: Sequence[Backend] = DEFAULT_BACKENDS,
        min_words: int = MIN_WORDS,
    ) -> None:
        self._http = http
        self._apify = apify
        self._backends = backends
        self._min_words = min_words

    async def extract(self, url: str, *, high_value: bool = False) -> Extracted | None:
        """Download the page (robots.txt respected) and extract it. None when nothing usable."""
        response = await self._http.get(url, respect_robots=True)
        if response.status_code >= 400:
            log.debug("extract_http_error", status=response.status_code)
            html = ""
        else:
            html = response.text
        best: Extracted | None = None
        for backend in self._backends:
            result = await self._run(backend, html, url) if html else None
            best = _longer(best, result)
            if best and word_count(best.text) >= self._min_words:
                break
        else:
            if (
                self._apify
                and high_value
                and (best is None or word_count(best.text) < self._min_words)
            ):
                best = _longer(best, await self._apify.extract(url))
        if best is not None and best.language is None:
            best.language = detect_language(best.text)
        return best

    @staticmethod
    async def _run(backend: Backend, html: str, url: str) -> Extracted | None:
        try:
            return await asyncio.to_thread(backend, html, url)
        except Exception as exc:  # parsers raise broadly on malformed pages
            log.info("extract_backend_error", backend=backend.__name__, error=type(exc).__name__)
            return None


def _longer(a: Extracted | None, b: Extracted | None) -> Extracted | None:
    if a is None:
        return b
    if b is None:
        return a
    return b if word_count(b.text) > word_count(a.text) else a
