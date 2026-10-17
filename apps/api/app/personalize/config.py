"""Ranking weights and selection parameters. Change numbers here, not in the scoring code."""

import itertools
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScoreWeights:
    """The six components sum to 1.0, so a perfect article scores 1.0 before the multiplier."""

    semantic: float = 0.40
    topic: float = 0.20
    match: float = 0.15
    recency: float = 0.10
    importance: float = 0.10
    novelty: float = 0.05


@dataclass(frozen=True, slots=True)
class ScoringConfig:
    weights: ScoreWeights = ScoreWeights()
    recency_half_life_hours: float = 12.0
    # importance saturates when this many outlets cover a story
    importance_saturation_size: int = 10
    # source_affinity in [-1, 1] maps to a multiplier in [1 - spread, 1 + spread]
    affinity_spread: float = 0.5
    seen_penalty: float = 0.25
    low_quality_penalty: float = 0.10
    low_quality_below: float = 0.4


@dataclass(frozen=True, slots=True)
class SelectionConfig:
    mmr_lambda: float = 0.7
    max_per_source: int = 2
    explore_share: float = 0.15
    explore_min_quality: float = 0.6
    # explore picks come from outside the reader's N strongest topics
    top_topic_count: int = 5
    # MMR runs over this many best-scored candidates (it is O(pool x picks) in similarity maths)
    mmr_pool: int = 80


# reading_minutes -> number of items, linearly interpolated between these anchors
ITEMS_BY_MINUTES: tuple[tuple[int, int], ...] = ((5, 8), (10, 14), (20, 22))

RETRIEVAL_WINDOW_HOURS = 24
RETRIEVAL_VECTOR_LIMIT = 300
RETRIEVAL_KEYWORD_LIMIT = 200
RETRIEVAL_BIG_STORY_LIMIT = 30
RETRIEVAL_BIG_STORY_MIN_SIZE = 2
SEEN_EDITIONS_LOOKBACK = 7


def item_count(reading_minutes: int) -> int:
    """5 -> 8, 10 -> 14, 20 -> 22; in between is interpolated, outside is clamped."""
    points = ITEMS_BY_MINUTES
    if reading_minutes <= points[0][0]:
        return points[0][1]
    for (m0, n0), (m1, n1) in itertools.pairwise(points):
        if reading_minutes <= m1:
            return round(n0 + (n1 - n0) * (reading_minutes - m0) / (m1 - m0))
    return points[-1][1]


DEFAULT_SCORING = ScoringConfig()
DEFAULT_SELECTION = SelectionConfig()


@dataclass(frozen=True, slots=True)
class SignalWeights:
    """What each reader action is worth, as evidence about the story's topics and sources."""

    open: float = 1.0
    dwell: float = 0.8  # scaled by dwell time against the expected reading time
    more_like: float = 1.5
    save: float = 1.2
    quiz_correct: float = 0.3
    impression_only: float = -0.05  # shown, never opened
    skip: float = -0.6
    less_like: float = -1.5
    # onboarding taste-test answers count for less than behaviour in the paper
    onboarding_scale: float = 0.5


@dataclass(frozen=True, slots=True)
class LearningConfig:
    signals: SignalWeights = SignalWeights()
    half_life_days: float = 14.0
    dwell_min_seconds: float = 30.0
    default_reading_seconds: float = 90.0
    reading_words_per_minute: float = 230.0
    reading_seconds_range: tuple[float, float] = (30.0, 300.0)
    # an article counts as liked/disliked once its net signal reaches +/- this
    positive_threshold: float = 0.3
    negative_threshold: float = -0.3
    # topics: EMA step, and how much evidence (signal mass) it takes to trust a batch
    topic_alpha: float = 0.3
    topic_confidence_mass: float = 1.0
    # nightly multiplier for topics that got no signal at all
    topic_idle_decay: float = 0.995
    # Rocchio: v' = normalise(a v + b mean(pos) - c mean(neg))
    rocchio_alpha: float = 0.8
    rocchio_beta: float = 0.25
    rocchio_gamma: float = 0.1
    entity_promote_after: int = 3
    block_topic_after_less_likes: int = 3
    # affinity = (pos - neg) / (pos + neg + prior): a source needs a few actions to move far
    affinity_prior: float = 2.0
    # explore
    explore_graduate_weight: float = 0.4
    explore_ignored_min_shown: int = 3
    explore_engaged_min_share: float = 0.2
    explore_decay: float = 0.8
    explore_floor: float = 0.05
    # events older than this are never replayed
    lookback_days: int = 30
    # signals that trigger an incremental run right after an event batch
    strong_events: tuple[str, ...] = ("more_like", "less_like", "save")
    settled_memory: int = 300


DEFAULT_LEARNING = LearningConfig()
