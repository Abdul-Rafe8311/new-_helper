from app.personalize.config import SelectionConfig
from app.personalize.score import score_all
from app.personalize.select import select_items, topic_label, why_text
from app.personalize.types import Candidate, Scored
from tests.personalize_helpers import NOW, candidate, profile, uid


def scored(c: Candidate, score: float, **breakdown: object) -> Scored:
    base = {
        "components": {"match": 0.0, "topic": 0.0, "importance": 0.0},
        "raw": {"importance": 0.0, "recency": 1.0},
        "terms": [],
        "topic": None,
        "cluster_size": 1,
    }
    base.update(breakdown)
    return Scored(c, score, base)


def test_minutes_decide_how_many_items() -> None:
    cands = [candidate(cluster_id=i) for i in range(40)]
    ranked = score_all(cands, profile(), NOW)
    assert len(select_items(ranked, profile(reading_minutes=5, surprise_me=False))) == 8
    assert len(select_items(ranked, profile(reading_minutes=10, surprise_me=False))) == 14
    assert len(select_items(ranked, profile(reading_minutes=20, surprise_me=False))) == 22


def test_fewer_candidates_than_slots_returns_all_eligible() -> None:
    ranked = score_all([candidate(cluster_id=i) for i in range(3)], profile(), NOW)
    assert len(select_items(ranked, profile(reading_minutes=20))) == 3


def test_at_most_two_per_source_and_one_per_cluster() -> None:
    src = uid(1)
    same_source = [candidate(source_id=src, cluster_id=i, topics={"ai": 0.9}) for i in range(5)]
    twins = [candidate(cluster_id=99, topics={"ai": 0.9}) for _ in range(3)]
    p = profile(topics={"ai": 1.0}, surprise_me=False, reading_minutes=20)
    out = select_items(score_all([*same_source, *twins], p, NOW), p)
    assert sum(s.scored.candidate.source_id == src for s in out) == 2
    assert sum(s.scored.candidate.cluster_id == 99 for s in out) == 1


def test_mmr_prefers_a_different_story_over_a_near_duplicate() -> None:
    a = candidate(embedding=[1.0, 0.0], cluster_id=1)
    twin = candidate(embedding=[0.999, 0.01], cluster_id=2)
    other = candidate(embedding=[0.0, 1.0], cluster_id=3)
    ranked = [scored(a, 1.0), scored(twin, 0.95), scored(other, 0.7)]
    p = profile(reading_minutes=5, surprise_me=False)
    cfg = SelectionConfig(mmr_lambda=0.7)
    ids = [s.scored.candidate.id for s in select_items(ranked, p, cfg)]
    assert ids[:2] == [a.id, other.id]  # the twin is relegated behind the diverse pick
    assert ids[2] == twin.id


def test_lambda_one_is_pure_relevance() -> None:
    a = candidate(embedding=[1.0, 0.0], cluster_id=1)
    twin = candidate(embedding=[0.999, 0.01], cluster_id=2)
    other = candidate(embedding=[0.0, 1.0], cluster_id=3)
    ranked = [scored(a, 1.0), scored(twin, 0.95), scored(other, 0.7)]
    out = select_items(ranked, profile(surprise_me=False), SelectionConfig(mmr_lambda=1.0))
    assert [s.scored.candidate.id for s in out] == [a.id, twin.id, other.id]


def _explore_setup(surprise: bool, minutes: int = 10):
    p = profile(topics={"ai": 1.0, "cricket": 0.8}, surprise_me=surprise, reading_minutes=minutes)
    on = [candidate(cluster_id=i, topics={"ai": 0.9}) for i in range(30)]
    outside = [
        candidate(cluster_id=100 + i, topics={"space": 0.9}, source_quality=0.9) for i in range(6)
    ]
    shabby = candidate(cluster_id=200, topics={"space": 0.9}, source_quality=0.3)
    return p, on, outside, shabby


def test_explore_slots_reserve_about_fifteen_percent_from_outside_top_topics() -> None:
    p, on, outside, shabby = _explore_setup(True)
    out = select_items(score_all([*on, *outside, shabby], p, NOW), p)
    explore = [s for s in out if s.explore]
    assert len(out) == 14
    assert len(explore) == 2  # round(0.15 * 14)
    for s in explore:
        assert "space" in s.scored.candidate.topics
        assert s.scored.candidate.source_quality >= 0.6
        assert s.why.startswith("Outside your usual beats")
    assert shabby.id not in {s.scored.candidate.id for s in out}


def test_explore_slot_count_scales_with_the_paper() -> None:
    for minutes, expected in ((5, 1), (10, 2), (20, 3)):
        p, on, outside, _ = _explore_setup(True, minutes)
        out = select_items(score_all([*on, *outside], p, NOW), p)
        assert sum(s.explore for s in out) == expected


def test_no_explore_when_surprise_me_is_off() -> None:
    p, on, outside, _ = _explore_setup(False)
    out = select_items(score_all([*on, *outside], p, NOW), p)
    assert not any(s.explore for s in out)
    assert all("space" not in s.scored.candidate.topics for s in out)


def test_explore_respects_source_cap_and_falls_back_when_nothing_qualifies() -> None:
    p = profile(topics={"ai": 1.0}, surprise_me=True, reading_minutes=10)
    src = uid(5)
    outside = [
        candidate(cluster_id=i, topics={"space": 0.9}, source_id=src, source_quality=0.9)
        for i in range(5)
    ]
    on = [candidate(cluster_id=50 + i, topics={"ai": 0.9}) for i in range(20)]
    out = select_items(score_all([*outside, *on], p, NOW), p)
    assert sum(s.scored.candidate.source_id == src for s in out) == 2
    only_on = select_items(score_all(on, p, NOW), p)
    assert len(only_on) == 14
    assert not any(s.explore for s in only_on)


def test_selection_is_deterministic() -> None:
    p, on, outside, _ = _explore_setup(True)
    ranked = score_all([*on, *outside], p, NOW)
    assert select_items(ranked, p) == select_items(list(ranked), p)


def test_why_prefers_the_strongest_explainable_component() -> None:
    c = candidate()
    match = scored(
        c,
        0.5,
        components={"match": 0.15, "topic": 0.05, "importance": 0.02},
        terms=["Pakistan cricket"],
        topic="cricket",
    )
    assert why_text(match) == "Because you follow Pakistan cricket"
    topic = scored(c, 0.5, components={"match": 0.0, "topic": 0.12, "importance": 0.02}, topic="f1")
    assert why_text(topic) == "Because you follow Formula 1"
    big = scored(
        c,
        0.5,
        components={"match": 0.0, "topic": 0.0, "importance": 0.09},
        cluster_size=9,
    )
    assert why_text(big) == "Big story: 9 outlets covering it"


def test_why_falls_back_to_semantic_and_labels_explore() -> None:
    plain = scored(candidate(), 0.5)
    assert why_text(plain) == "Similar to what you like to read"
    weak_big = scored(
        candidate(), 0.5, components={"match": 0, "topic": 0, "importance": 0.01}, cluster_size=2
    )
    assert why_text(weak_big) == "Similar to what you like to read"
    assert why_text(scored(candidate(), 0.5, topic="space"), explore=True) == (
        "Outside your usual beats: " + topic_label("space")
    )
    assert why_text(plain, explore=True) == "Outside your usual beats"
