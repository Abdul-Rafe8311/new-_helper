from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.onboarding.headlines import Candidate, Pick, pick_headlines

NOW = datetime(2026, 10, 17, 6, tzinfo=UTC)


def cand(
    n: int,
    topic: str,
    *,
    source: str | None = None,
    image: bool = True,
    cluster: int | None = None,
    quality: float = 0.5,
    age_hours: int = 1,
) -> Candidate:
    return Candidate(
        id=UUID(int=n),
        headline=f"A reasonably long headline number {n}",
        source=source or f"Source {n}",
        image_url="https://img.example/x.jpg" if image else None,
        topics={topic: 0.8},
        cluster_id=cluster,
        quality=quality,
        published=NOW - timedelta(hours=age_hours),
    )


def deck(topics: list[str], per_topic: int = 6, outside: int = 4) -> list[Candidate]:
    n = 0
    out: list[Candidate] = []
    for topic in [*topics, "gaming", "books", "travel", "food"][: len(topics) + outside]:
        for _ in range(per_topic):
            n += 1
            out.append(cand(n, topic, age_hours=n % 20))
    return out


def topics_of(picks: list[Pick]) -> list[str | None]:
    return [p.topic for p in picks]


def test_twelve_picks_with_three_outside_the_chosen_topics() -> None:
    chosen = ["ai", "cricket", "f1"]
    picks = pick_headlines(deck(chosen), chosen)
    assert len(picks) == 12
    assert sum(p.outside for p in picks) == 3
    assert all(p.topic not in chosen for p in picks if p.outside)
    assert all(p.topic in chosen for p in picks if not p.outside)
    assert len({p.candidate.id for p in picks}) == 12


def test_every_chosen_topic_is_represented() -> None:
    chosen = ["ai", "cricket", "f1", "space"]
    picks = pick_headlines(deck(chosen), chosen)
    assert set(chosen) <= set(topics_of(picks))


def test_outside_picks_are_spread_out_and_differ() -> None:
    chosen = ["ai", "cricket", "f1"]
    picks = pick_headlines(deck(chosen), chosen)
    positions = [i for i, p in enumerate(picks) if p.outside]
    assert len(positions) == 3
    assert positions[0] > 0
    assert positions[-1] < len(picks) - 1
    assert len({picks[i].topic for i in positions}) == 3


def test_deterministic() -> None:
    chosen = ["ai", "cricket", "f1"]
    candidates = deck(chosen)
    first = [p.candidate.id for p in pick_headlines(candidates, chosen)]
    second = [p.candidate.id for p in pick_headlines(list(reversed(candidates)), chosen)]
    assert first == second


def test_one_story_per_cluster_and_two_per_source() -> None:
    chosen = ["ai"]
    candidates = [cand(i, "ai", cluster=1) for i in range(1, 4)]
    candidates += [cand(10 + i, "ai", source="Same Wire") for i in range(5)]
    picks = pick_headlines(candidates, chosen, total=12)
    assert sum(1 for p in picks if p.candidate.cluster_id == 1) == 1
    assert sum(1 for p in picks if p.candidate.source == "Same Wire") == 2


def test_prefers_pictures_then_quality() -> None:
    plain = cand(1, "ai", image=False, quality=0.99)
    pretty = cand(2, "ai", image=True, quality=0.1)
    picks = pick_headlines([plain, pretty], ["ai"], total=1, outside=0)
    assert [p.candidate.id for p in picks] == [pretty.id]


def test_tops_up_when_a_topic_has_little_news() -> None:
    chosen = ["ai", "cricket", "f1"]
    candidates = [cand(i, "ai") for i in range(1, 9)] + [cand(20, "cricket")]
    picks = pick_headlines(candidates, chosen)
    assert len(picks) == len(candidates)  # nothing to drop, nothing invented


def test_no_candidates_no_picks() -> None:
    assert pick_headlines([], ["ai", "cricket", "f1"]) == []
    assert uuid4()  # keep the import honest


def test_top_up_from_other_topics_counts_as_outside() -> None:
    chosen = ["ai", "cricket", "f1"]
    candidates = [cand(1, "ai"), cand(2, "cricket")] + [cand(10 + i, "books") for i in range(8)]
    picks = pick_headlines(candidates, chosen, total=6, outside=1)
    assert len(picks) == 6
    assert all(p.outside for p in picks if p.topic == "books")
    assert not any(p.outside for p in picks if p.topic in chosen)
