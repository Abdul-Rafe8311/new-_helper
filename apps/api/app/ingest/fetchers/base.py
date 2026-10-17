"""The contract every fetcher satisfies, and helpers they share."""

import re
from calendar import timegm
from datetime import UTC, datetime
from html import unescape
from time import struct_time
from typing import Protocol

from app.ingest.types import FetchResult

_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")


class FetchError(Exception):
    """A source could not be fetched or parsed; counts toward its failure_count."""


class Fetcher(Protocol):
    """One unit of fetching work: a feed, an API query, a Google News search."""

    label: str

    async def fetch(self) -> FetchResult: ...


def strip_html(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = _SPACE.sub(" ", unescape(_TAG.sub(" ", text))).strip()
    return cleaned or None


def struct_to_datetime(value: struct_time | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(timegm(value), tz=UTC)


def epoch_to_datetime(value: float | int | None) -> datetime | None:
    return None if value is None else datetime.fromtimestamp(value, tz=UTC)
