"""Demand-driven Google News queries: what today's readers care about, deduped and capped."""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from app.ingest.fetchers.google_news import PAKISTAN, US, Locale

MAX_QUERIES = 100
MIN_TERM_CHARS = 3
PAKISTAN_TIMEZONES = frozenset({"Asia/Karachi"})


@dataclass(frozen=True)
class ReaderInterests:
    keywords: list[str]
    entities: dict[str, list[str]]
    timezone: str = "UTC"


@dataclass(frozen=True)
class NewsQuery:
    text: str
    locale: Locale


def _terms(reader: ReaderInterests) -> set[str]:
    raw = [*reader.keywords, *(v for values in reader.entities.values() for v in values)]
    cleaned = {" ".join(t.split()) for t in raw}
    return {t for t in cleaned if len(t) >= MIN_TERM_CHARS}


def build_queries(readers: Iterable[ReaderInterests], cap: int = MAX_QUERIES) -> list[NewsQuery]:
    """Union of every reader's keywords and entities, case-insensitively deduped.

    Terms wanted by more readers come first (so the cap drops the long tail). Terms from a reader
    in Pakistan are also searched against the Pakistan edition. At most `cap` searches are made.
    """
    demand: Counter[str] = Counter()
    display: dict[str, str] = {}
    local: set[str] = set()
    for reader in readers:
        for term in _terms(reader):
            key = term.casefold()
            demand[key] += 1
            display.setdefault(key, term)
            if reader.timezone in PAKISTAN_TIMEZONES:
                local.add(key)
    ordered = sorted(demand, key=lambda k: (-demand[k], k))
    queries: list[NewsQuery] = []
    for key in ordered:
        for locale in _locales(key in local):
            if len(queries) >= cap:
                return queries
            queries.append(NewsQuery(display[key], locale))
    return queries


def _locales(is_local: bool) -> list[Locale]:
    return [US, PAKISTAN] if is_local else [US]
