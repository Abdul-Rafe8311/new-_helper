"""Turn raw reader events into one signed weight per story.

Events are collapsed per edition item first: opens count once, dwell takes the longest stretch,
and the toggles (skip, save, more_like, less_like) keep the reader's last word, where a value of
0 retracts them. The weights live in `SignalWeights`; older events count for less (half-life).

This module is pure: the database layer feeds it `RawEvent`s and a reading-time lookup.
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.personalize.config import DEFAULT_LEARNING, LearningConfig

OPEN_TYPES = frozenset({"open", "mark_read"})
TOGGLE_TYPES = ("skip", "save", "more_like", "less_like")


@dataclass(frozen=True, slots=True)
class RawEvent:
    """The learner's view of a `reader_events` row."""

    type: str
    item_id: UUID | None
    article_id: UUID
    created_at: datetime
    value: float | None = None
    meta: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StorySignal:
    """What the reader's behaviour says about one story, with the parts that add up to it."""

    item_id: UUID | None
    article_id: UUID
    weight: float
    parts: Mapping[str, float]
    last_at: datetime

    @property
    def strong(self) -> bool:
        return any(name in self.parts for name in ("more_like", "less_like", "save"))


def decay(age_days: float, half_life_days: float) -> float:
    """0.5 ** (age / half-life); events from the future count in full."""
    return float(0.5 ** (max(0.0, age_days) / half_life_days))


def expected_reading_seconds(
    word_count: int | None, cfg: LearningConfig = DEFAULT_LEARNING
) -> float:
    lo, hi = cfg.reading_seconds_range
    if not word_count or word_count <= 0:
        return cfg.default_reading_seconds
    return max(lo, min(hi, word_count / cfg.reading_words_per_minute * 60))


def dwell_weight(seconds: float, expected: float, cfg: LearningConfig = DEFAULT_LEARNING) -> float:
    """0 under the minimum dwell; otherwise the dwell weight scaled by how much of the story
    the reader plausibly read (capped at all of it)."""
    if seconds < cfg.dwell_min_seconds:
        return 0.0
    return cfg.signals.dwell * min(1.0, seconds / expected)


def _toggled(events: list[RawEvent], kind: str) -> bool:
    """Last event of this kind wins; value 0 retracts."""
    last = max((e for e in events if e.type == kind), key=lambda e: e.created_at, default=None)
    return last is not None and (last.value is None or last.value > 0)


def _is_correct(event: RawEvent) -> bool:
    if event.meta.get("correct") is True:
        return True
    return event.value is not None and event.value > 0 and event.meta.get("correct") is None


def story_signals(
    events: Iterable[RawEvent],
    now: datetime,
    reading_words: Mapping[UUID, int | None] | None = None,
    cfg: LearningConfig = DEFAULT_LEARNING,
) -> list[StorySignal]:
    """One signed, time-decayed weight per story the events touch (stories with net 0 are dropped).

    `reading_words` maps article id -> word count, used to judge how long a read should take.
    """
    words = reading_words or {}
    w = cfg.signals
    by_story: dict[tuple[UUID | None, UUID], list[RawEvent]] = defaultdict(list)
    for e in events:
        by_story[(e.item_id, e.article_id)].append(e)

    out: list[StorySignal] = []
    for (item_id, article_id), group in by_story.items():
        parts: dict[str, float] = {}
        opened = any(e.type in OPEN_TYPES for e in group)
        if opened:
            parts["open"] = w.open
        longest = max((e.value or 0.0 for e in group if e.type == "dwell"), default=0.0)
        dwell = dwell_weight(longest, expected_reading_seconds(words.get(article_id), cfg), cfg)
        if dwell:
            parts["dwell"] = dwell
        for kind, weight in (
            ("more_like", w.more_like),
            ("save", w.save),
            ("skip", w.skip),
            ("less_like", w.less_like),
        ):
            if _toggled(group, kind):
                parts[kind] = weight
        if any(e.type == "quiz_answer" and _is_correct(e) for e in group):
            parts["quiz_correct"] = w.quiz_correct
        for e in group:
            if e.type == "onboarding_like":
                parts["onboarding_like"] = w.open * w.onboarding_scale
            elif e.type == "onboarding_skip":
                parts["onboarding_skip"] = w.skip * w.onboarding_scale
        if not parts and any(e.type == "impression" for e in group):
            parts["impression_only"] = w.impression_only  # shown, never touched
        if not parts:
            continue
        last_at = max(e.created_at for e in group)
        age_days = (now - last_at).total_seconds() / 86400
        factor = decay(age_days, cfg.half_life_days)
        total = sum(parts.values()) * factor
        if total == 0.0:
            continue
        out.append(StorySignal(item_id, article_id, total, parts, last_at))
    out.sort(key=lambda s: (s.last_at, str(s.article_id)))
    return out
