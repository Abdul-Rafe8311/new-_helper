from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from app.personalize.config import DEFAULT_LEARNING
from app.personalize.signals import (
    RawEvent,
    StorySignal,
    decay,
    dwell_weight,
    expected_reading_seconds,
    story_signals,
)

NOW = datetime(2026, 10, 17, 22, 0, tzinfo=UTC)
ART = UUID(int=1)
ITEM = UUID(int=2)
W = DEFAULT_LEARNING.signals


def ev(kind: str, value: float | None = None, *, minutes: int = 0, **meta: object) -> RawEvent:
    return RawEvent(kind, ITEM, ART, NOW - timedelta(minutes=minutes), value, meta)


def story(*events: RawEvent, words: int | None = None) -> StorySignal:
    out = story_signals(events, NOW, {ART: words})
    assert len(out) == 1
    return out[0]


def net(*events: RawEvent, words: int | None = None) -> float:
    """The story's net weight; 0 when the events add up to nothing."""
    out = story_signals(events, NOW, {ART: words})
    return out[0].weight if out else 0.0


@pytest.mark.parametrize(
    ("event", "expected"),
    [
        ("open", W.open),
        ("more_like", W.more_like),
        ("save", W.save),
        ("skip", W.skip),
        ("less_like", W.less_like),
        ("impression", W.impression_only),
    ],
)
def test_each_event_has_its_configured_weight(event: str, expected: float) -> None:
    assert net(ev(event)) == pytest.approx(expected, rel=1e-3)


def test_weights_match_the_spec() -> None:
    assert (W.open, W.dwell, W.more_like, W.save, W.quiz_correct) == (1.0, 0.8, 1.5, 1.2, 0.3)
    assert (W.impression_only, W.skip, W.less_like) == (-0.05, -0.6, -1.5)


def test_mark_read_counts_as_an_open() -> None:
    assert story(ev("mark_read")).parts == {"open": W.open}


def test_impression_with_an_open_is_not_penalised() -> None:
    sig = story(ev("impression"), ev("open"))
    assert "impression_only" not in sig.parts
    assert sig.weight == pytest.approx(W.open, rel=1e-3)


def test_dwell_under_thirty_seconds_counts_for_nothing() -> None:
    assert net(ev("dwell", 29)) == 0.0


def test_dwell_is_scaled_by_expected_reading_time() -> None:
    # 920 words = 240 s of reading at 230 wpm; 60 s is a quarter of it
    assert net(ev("dwell", 60), words=920) == pytest.approx(W.dwell * 0.25, rel=1e-3)
    assert net(ev("dwell", 240), words=920) == pytest.approx(W.dwell, rel=1e-3)
    assert net(ev("dwell", 900), words=920) == pytest.approx(W.dwell, rel=1e-3)  # capped


def test_dwell_takes_the_longest_stretch_not_the_sum() -> None:
    expected = dwell_weight(45, DEFAULT_LEARNING.default_reading_seconds)
    assert net(ev("dwell", 40), ev("dwell", 45)) == pytest.approx(expected)


def test_expected_reading_time_is_clamped_and_defaults_when_unknown() -> None:
    assert expected_reading_seconds(None) == DEFAULT_LEARNING.default_reading_seconds
    assert expected_reading_seconds(50) == 30.0
    assert expected_reading_seconds(100_000) == 300.0


def test_quiz_correct_adds_and_wrong_does_not() -> None:
    assert net(ev("quiz_answer", correct=True)) == pytest.approx(W.quiz_correct, rel=1e-3)
    assert net(ev("quiz_answer", correct=False)) == 0.0


def test_onboarding_answers_count_at_half_weight() -> None:
    assert net(ev("onboarding_like")) == pytest.approx(W.open * 0.5, rel=1e-3)
    assert net(ev("onboarding_skip")) == pytest.approx(W.skip * 0.5, rel=1e-3)


def test_signals_add_up() -> None:
    sig = story(ev("open"), ev("more_like"), ev("save"))
    assert sig.weight == pytest.approx(W.open + W.more_like + W.save, rel=1e-3)
    assert sig.strong


def test_open_alone_is_not_a_strong_signal() -> None:
    assert not story(ev("open")).strong


def test_toggles_keep_the_last_word_and_zero_retracts() -> None:
    assert net(ev("skip", minutes=5), ev("skip", 0, minutes=1)) == 0.0
    assert net(ev("skip", 0, minutes=5), ev("skip", 1, minutes=1)) == pytest.approx(
        W.skip, rel=1e-3
    )


def test_half_life_is_fourteen_days() -> None:
    assert DEFAULT_LEARNING.half_life_days == 14.0
    assert decay(14, 14) == pytest.approx(0.5)
    assert decay(28, 14) == pytest.approx(0.25)
    assert decay(0, 14) == 1.0
    assert decay(-3, 14) == 1.0


def test_old_events_weigh_less() -> None:
    old = net(ev("open", minutes=14 * 24 * 60))
    assert old == pytest.approx(net(ev("open")) / 2, rel=1e-3)


def test_stories_are_kept_apart_and_ordered_by_time() -> None:
    other = RawEvent("open", UUID(int=9), UUID(int=10), NOW - timedelta(hours=1))
    sigs = story_signals([ev("open"), other], NOW)
    assert [s.article_id for s in sigs] == [UUID(int=10), ART]
