from datetime import UTC, datetime, timedelta

import pytest

from app.ingest.normalise import DropReason, content_hash, drop_reason, normalise_text

NOW = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)
KW = {"allowed_languages": {"en"}, "now": NOW}


def test_hash_ignores_case_punctuation_and_whitespace() -> None:
    a = content_hash("Rates Held, Again!", "The bank  left rates\nunchanged today.")
    b = content_hash("rates held again", "the bank left rates unchanged today")
    assert a == b


def test_hash_differs_for_different_stories() -> None:
    assert content_hash("A", "one body") != content_hash("B", "one body")
    assert content_hash("A", "one body") != content_hash("A", "another body")


def test_hash_uses_only_the_first_thousand_characters() -> None:
    head = "x" * 1000
    assert content_hash("T", head + " tail one") == content_hash("T", head + " tail two")


def test_normalise_text_keeps_unicode_words() -> None:
    assert normalise_text("Lahore \u2014 Qalandars\u2019 win!") == "lahore qalandars win"


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"published_at": NOW - timedelta(hours=3), "word_count": 400, "language": "en"}, None),
        ({"published_at": NOW - timedelta(hours=47), "word_count": 400, "language": "en"}, None),
        (
            {"published_at": NOW - timedelta(hours=49), "word_count": 400, "language": "en"},
            DropReason.STALE,
        ),
        ({"published_at": None, "word_count": 400, "language": "en"}, None),
        ({"published_at": NOW, "word_count": 119, "language": "en"}, DropReason.SHORT),
        ({"published_at": NOW, "word_count": 120, "language": "en"}, None),
        ({"published_at": NOW, "word_count": 400, "language": "de"}, DropReason.LANGUAGE),
        ({"published_at": NOW, "word_count": 400, "language": "en-GB"}, None),
        ({"published_at": NOW, "word_count": 400, "language": None}, None),
    ],
)
def test_drop_reason(kwargs: dict[str, object], expected: DropReason | None) -> None:
    assert drop_reason(**kwargs, **KW) == expected  # type: ignore[arg-type]


def test_stale_wins_over_short() -> None:
    reason = drop_reason(
        published_at=NOW - timedelta(days=5),
        word_count=5,
        language="de",
        **KW,  # type: ignore[arg-type]
    )
    assert reason == DropReason.STALE
