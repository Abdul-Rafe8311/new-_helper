"""Content hashing and the drop rules applied to every candidate article."""

import hashlib
import re
from collections.abc import Collection
from datetime import datetime, timedelta
from enum import StrEnum

MAX_AGE = timedelta(hours=48)
MIN_WORDS = 120
HASH_TEXT_CHARS = 1000

_NON_WORD = re.compile(r"[^\w\s]", re.UNICODE)
_SPACE = re.compile(r"\s+")


class DropReason(StrEnum):
    STALE = "stale"
    SHORT = "short"
    LANGUAGE = "language"
    ROBOTS = "robots"
    EXTRACTION = "extraction"


def normalise_text(text: str) -> str:
    return _SPACE.sub(" ", _NON_WORD.sub(" ", text.casefold())).strip()


def content_hash(title: str, text: str) -> str:
    """sha256 over the normalised title plus the first 1000 normalised characters of the body.

    Normalising first makes the hash survive punctuation, casing and whitespace differences, so
    the same wire story republished by two outlets collapses to one article.
    """
    payload = f"{normalise_text(title)}\n{normalise_text(text)[:HASH_TEXT_CHARS]}"
    return hashlib.sha256(payload.encode()).hexdigest()


def is_stale(published_at: datetime | None, now: datetime) -> bool:
    return published_at is not None and now - published_at > MAX_AGE


def drop_reason(
    *,
    published_at: datetime | None,
    word_count: int,
    language: str | None,
    allowed_languages: Collection[str],
    now: datetime,
) -> DropReason | None:
    """Why an extracted article must not be stored, or None to keep it."""
    if is_stale(published_at, now):
        return DropReason.STALE
    if word_count < MIN_WORDS:
        return DropReason.SHORT
    if language is not None and language.split("-")[0].lower() not in allowed_languages:
        return DropReason.LANGUAGE
    return None
