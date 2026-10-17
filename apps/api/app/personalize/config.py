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
