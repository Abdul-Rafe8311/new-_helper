import math
from datetime import timedelta

import pytest

from app.personalize.config import ScoreWeights, ScoringConfig, item_count
from app.personalize.score import (
    cosine,
    importance_score,
    match_score,
    matched_terms,
    recency_score,
    score_all,
    score_candidate,
    source_multiplier,
)
from tests.personalize_helpers import NOW, candidate, profile


def test_default_weights_sum_to_one() -> None:
    w = ScoreWeights()
    total = w.semantic + w.topic + w.match + w.recency + w.importance + w.novelty
    assert total == pytest.approx(1.0)


def test_cosine() -> None:
    assert cosine([1, 0], [1, 0]) == pytest.approx(1.0)
    assert cosine([1, 0], [0, 1]) == pytest.approx(0.0)
    assert cosine([1, 1], [2, 2]) == pytest.approx(1.0)
    assert cosine([0, 0], [1, 1]) == 0.0


@pytest.mark.parametrize(
    ("minutes", "items"), [(3, 8), (5, 8), (10, 14), (15, 18), (20, 22), (45, 22)]
)
def test_item_count(minutes: int, items: int) -> None:
    assert item_count(minutes) == items


def test_recency_halves_every_twelve_hours() -> None:
    fresh = candidate(published_at=NOW)
    half = candidate(published_at=NOW - timedelta(hours=12))
    quarter = candidate(published_at=NOW - timedelta(hours=24))
    assert recency_score(fresh, NOW, 12) == pytest.approx(1.0)
    assert recency_score(half, NOW, 12) == pytest.approx(0.5)
    assert recency_score(quarter, NOW, 12) == pytest.approx(0.25)
    assert recency_score(candidate(published_at=None), NOW, 12) == 0.5


def test_importance_grows_with_coverage_and_scales_with_quality() -> None:
    one = importance_score(candidate(cluster_size=1, source_quality=1.0), 10)
    nine = importance_score(candidate(cluster_size=9, source_quality=1.0), 10)
    saturated = importance_score(candidate(cluster_size=50, source_quality=1.0), 10)
    assert one < nine < saturated == pytest.approx(1.0)
    assert importance_score(candidate(cluster_size=9, source_quality=0.5), 10) == pytest.approx(
        nine * 0.5
    )


def test_match_score_saturates() -> None:
    assert [match_score(n) for n in range(4)] == [0.0, 0.5, 0.75, 0.875]


def test_matched_terms_use_word_boundaries_and_extracted_entities() -> None:
    c = candidate(
        title="PSL final set for Lahore",
        summary="Anthropic released a model.",
        entities={"teams": ["Lahore Qalandars"]},
    )
    hits = matched_terms(c, ["psl", "Anthropic", "Lahore Qalandars", "AI", "final set"])
    assert hits == ["psl", "Anthropic", "Lahore Qalandars", "final set"]
    assert matched_terms(candidate(title="Paris sells"), ["PSL", "AI"]) == []


def test_source_multiplier_range() -> None:
    c = candidate()
    assert source_multiplier(c, profile(), 0.5) == 1.0
    assert source_multiplier(c, profile(source_affinity={str(c.source_id): 1.0}), 0.5) == 1.5
    assert source_multiplier(c, profile(source_affinity={str(c.source_id): -3}), 0.5) == 0.5


def test_score_is_the_documented_weighted_sum() -> None:
    cfg = ScoringConfig()
    c = candidate(
        embedding=[1.0, 0.0],
        topics={"cricket": 0.8},
        title="PSL news",
        cluster_size=9,
        source_quality=1.0,
    )
    p = profile(
        interest_vector=[1.0, 0.0],
        topics={"cricket": 0.5},
        keywords=["PSL"],
    )
    s = score_candidate(c, p, NOW, cfg)
    expected = (
        0.40 * 1.0  # semantic: identical direction
        + 0.20 * (0.8 * 0.5)  # topic: article score x profile weight
        + 0.15 * 0.5  # one keyword hit
        + 0.10 * 1.0  # published now
        + 0.10 * (math.log(10) / math.log(11))  # nine outlets, top quality
        + 0.05 * 0.5  # novelty: 1 - profile weight of the article's topic
    )
    assert s.score == pytest.approx(expected, abs=1e-4)
    assert s.breakdown["total"] == pytest.approx(s.score, abs=1e-5)
    assert set(s.breakdown["components"]) == {
        "semantic", "topic", "match", "recency", "importance", "novelty",
    }  # fmt: skip
    assert s.breakdown["topic"] == "cricket"
    assert s.breakdown["terms"] == ["PSL"]


def test_penalties_and_multiplier_apply_after_the_sum() -> None:
    c = candidate(embedding=[1.0, 0.0], source_quality=0.3)
    p = profile(interest_vector=[1.0, 0.0], source_affinity={str(c.source_id): 1.0})
    plain = score_candidate(c, p, NOW)
    seen = score_candidate(c, p, NOW, seen_ids=frozenset({c.id}))
    assert plain.breakdown["multiplier"] == 1.5
    assert plain.breakdown["penalties"] == {"low_quality": 0.1}
    assert seen.score == pytest.approx(plain.score - 0.25)
    assert seen.breakdown["penalties"] == {"low_quality": 0.1, "seen": 0.25}


def test_score_never_negative() -> None:
    c = candidate(source_quality=0.0, published_at=NOW - timedelta(days=30))
    p = profile(topics={"x": 1.0})
    s = score_candidate(c, p, NOW, seen_ids=frozenset({c.id}))
    assert s.score >= 0.0


def test_matching_beats_non_matching_and_ordering_is_deterministic() -> None:
    p = profile(interest_vector=[1.0, 0.0], topics={"ai": 0.9}, keywords=["agents"])
    on_topic = candidate(embedding=[0.9, 0.1], topics={"ai": 0.9}, title="Agents arrive")
    off_topic = candidate(embedding=[0.0, 1.0], topics={"gossip": 0.9})
    ranked = score_all([off_topic, on_topic], p, NOW)
    assert [s.candidate.id for s in ranked] == [on_topic.id, off_topic.id]
    assert score_all([on_topic, off_topic], p, NOW) == ranked
