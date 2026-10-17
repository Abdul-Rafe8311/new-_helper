import math
from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.personalize.config import DEFAULT_LEARNING as CFG
from app.personalize.learn import (
    LearnerState,
    StoryFacts,
    block_topics,
    learn,
    promote_entities,
    rocchio,
    tune_explore,
    update_sources,
    update_topics,
    update_vector,
)
from app.personalize.signals import StorySignal

NOW = datetime(2026, 10, 17, 22, 0, tzinfo=UTC)
_n = iter(range(1, 10_000))


def pair(
    weight: float,
    *,
    topics: dict[str, float] | None = None,
    embedding: list[float] | None = None,
    entities: dict[str, list[str]] | None = None,
    source: str | None = None,
    explore: bool = False,
    parts: dict[str, float] | None = None,
) -> tuple[StorySignal, StoryFacts]:
    aid = UUID(int=next(_n))
    sig = StorySignal(aid, aid, weight, parts or {"open": weight}, NOW)
    facts = StoryFacts(aid, topics or {}, entities or {}, embedding, source, explore)
    return sig, facts


def norm(v: list[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


# topics ---------------------------------------------------------------------------------------


def test_topic_moves_towards_one_on_positive_evidence() -> None:
    state = LearnerState(topics={"ai": 0.5})
    changes = update_topics(state, [pair(1.0, topics={"ai": 0.9})], CFG, idle_decay=False)
    assert 0.5 < state.topics["ai"] < 1.0
    (change,) = changes
    assert (change.kind, change.key) == ("topic_weight", "ai")
    assert change.delta == pytest.approx(state.topics["ai"] - 0.5, abs=1e-5)
    assert change.signals[0]["type"] == "open"


def test_topic_moves_towards_zero_on_negative_evidence() -> None:
    state = LearnerState(topics={"sports": 0.5})
    update_topics(state, [pair(-1.5, topics={"sports": 0.9})], CFG, idle_decay=False)
    assert state.topics["sports"] < 0.5


def test_topic_step_is_an_ema_of_the_target() -> None:
    state = LearnerState(topics={"ai": 0.0})
    update_topics(state, [pair(1.0, topics={"ai": 1.0})], CFG, idle_decay=False)
    # evidence 1.0 -> confidence 1/(1+1) = 0.5 -> step = alpha * confidence * (1 - 0)
    assert state.topics["ai"] == pytest.approx(CFG.topic_alpha * 0.5)


def test_more_evidence_means_a_bigger_step() -> None:
    one, many = LearnerState(topics={"ai": 0.2}), LearnerState(topics={"ai": 0.2})
    update_topics(one, [pair(1.0, topics={"ai": 1.0})], CFG, idle_decay=False)
    update_topics(many, [pair(1.0, topics={"ai": 1.0}) for _ in range(6)], CFG, idle_decay=False)
    assert many.topics["ai"] > one.topics["ai"]


def test_topic_weights_stay_between_zero_and_one() -> None:
    state = LearnerState(topics={"ai": 0.99, "sports": 0.01})
    batch = [pair(3.0, topics={"ai": 1.0}) for _ in range(20)]
    batch += [pair(-3.0, topics={"sports": 1.0}) for _ in range(20)]
    update_topics(state, batch, CFG, idle_decay=False)
    assert 0.0 <= state.topics["sports"] <= state.topics["ai"] <= 1.0


def test_a_new_topic_is_learned_from_positive_evidence() -> None:
    state = LearnerState()
    update_topics(state, [pair(1.0, topics={"health": 0.8})], CFG, idle_decay=False)
    assert state.topics["health"] > 0


def test_topics_without_any_signal_decay_slowly_at_night() -> None:
    state = LearnerState(topics={"ai": 0.5, "health": 0.4})
    changes = update_topics(state, [pair(1.0, topics={"ai": 1.0})], CFG, idle_decay=True)
    assert state.topics["health"] == pytest.approx(0.4 * CFG.topic_idle_decay)
    decay = next(c for c in changes if c.kind == "topic_decay")
    assert set(decay.after) == {"health"}


def test_incremental_runs_do_not_decay_idle_topics() -> None:
    state = LearnerState(topics={"health": 0.4})
    assert update_topics(state, [], CFG, idle_decay=False) == []
    assert state.topics["health"] == 0.4


# interest vector ------------------------------------------------------------------------------


def test_rocchio_formula_and_normalisation() -> None:
    v, pos, neg = [1.0, 0.0], [[0.0, 1.0], [0.0, 1.0]], [[1.0, 0.0]]
    out = rocchio(v, pos, neg)
    raw = [0.8 * 1.0 + 0.25 * 0.0 - 0.1 * 1.0, 0.0 + 0.25 * 1.0 - 0.0]
    assert out == pytest.approx([x / norm(raw) for x in raw])
    assert norm(out or []) == pytest.approx(1.0)


def test_rocchio_uses_the_mean_of_the_positives() -> None:
    out = rocchio([1.0, 0.0, 0.0], [[0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], [])
    raw = [0.8, 0.125, 0.125]
    assert out == pytest.approx([x / norm(raw) for x in raw])


def test_rocchio_starts_from_nothing() -> None:
    assert rocchio(None, [[0.0, 2.0]], []) == pytest.approx([0.0, 1.0])


def test_rocchio_pulls_towards_liked_and_away_from_disliked() -> None:
    like, dislike = [0.0, 1.0], [1.0, 0.0]
    out = rocchio([0.6, 0.8], [like], [dislike])
    assert out is not None
    assert out[1] > 0.8
    assert out[0] < 0.6


def test_rocchio_without_feedback_changes_nothing() -> None:
    assert rocchio([1.0, 0.0], [], []) == [1.0, 0.0]
    assert rocchio(None, [], []) is None


def test_update_vector_uses_only_clear_signals_and_logs_the_move() -> None:
    state = LearnerState(interest_vector=[1.0, 0.0])
    batch = [
        pair(1.0, embedding=[0.0, 1.0]),
        pair(0.1, embedding=[5.0, 5.0]),  # too weak to count
        pair(-1.0, embedding=[1.0, 0.0]),
    ]
    (change,) = update_vector(state, batch, CFG)
    assert change.kind == "interest_vector"
    assert change.delta is not None
    assert change.delta > 0
    assert state.interest_vector is not None
    assert state.interest_vector[1] == pytest.approx(0.25 / norm([0.7, 0.25]))


def test_update_vector_skips_stories_without_embeddings() -> None:
    state = LearnerState(interest_vector=[1.0, 0.0])
    assert update_vector(state, [pair(1.0)], CFG) == []
    assert state.interest_vector == [1.0, 0.0]


# entities -------------------------------------------------------------------------------------


def named(who: str) -> dict[str, list[str]]:
    return {"people": [who]}


def test_entity_is_promoted_after_three_liked_stories() -> None:
    state = LearnerState(entities={"people": []})
    batch = [pair(1.0, entities=named("Ada Lovelace")) for _ in range(3)]
    (change,) = promote_entities(state, batch, CFG)
    assert change.kind == "entity_promoted"
    assert change.key == "Ada Lovelace"
    assert state.entities["people"] == ["Ada Lovelace"]
    assert state.learned_entities["people"] == ["Ada Lovelace"]


def test_two_stories_are_not_enough() -> None:
    state = LearnerState()
    assert promote_entities(state, [pair(1.0, entities=named("Ada")) for _ in range(2)], CFG) == []
    assert not state.entities


def test_entity_counts_accumulate_across_runs() -> None:
    state = LearnerState()
    assert promote_entities(state, [pair(1.0, entities=named("Ada"))] * 2, CFG) == []
    (change,) = promote_entities(state, [pair(1.0, entities=named("Ada"))], CFG)
    assert change.key == "Ada"


def test_only_liked_stories_count_towards_an_entity() -> None:
    state = LearnerState()
    batch = [pair(1.0, entities=named("Ada")) for _ in range(2)]
    batch += [pair(-1.0, entities=named("Ada")) for _ in range(5)]
    assert promote_entities(state, batch, CFG) == []


def test_a_known_entity_is_not_promoted_again() -> None:
    state = LearnerState(entities={"people": ["ada"]})
    assert promote_entities(state, [pair(1.0, entities=named("Ada")) for _ in range(5)], CFG) == []
    assert not state.learned_entities


# blocking -------------------------------------------------------------------------------------


def disliked(topic: str) -> tuple[StorySignal, StoryFacts]:
    return pair(-1.5, topics={topic: 0.9}, parts={"less_like": -1.5})


def test_topic_is_blocked_after_repeated_less_like() -> None:
    state = LearnerState()
    assert block_topics(state, [disliked("sports"), disliked("sports")], CFG) == []
    (change,) = block_topics(state, [disliked("sports")], CFG)
    assert (change.kind, change.key) == ("topic_blocked", "sports")
    assert state.blocked_topics == ["sports"]


def test_skips_alone_never_block_a_topic() -> None:
    state = LearnerState()
    batch = [pair(-0.6, topics={"sports": 0.9}, parts={"skip": -0.6}) for _ in range(10)]
    assert block_topics(state, batch, CFG) == []


def test_a_blocked_topic_is_only_logged_once() -> None:
    state = LearnerState(blocked_topics=["sports"])
    assert block_topics(state, [disliked("sports")] * 4, CFG) == []
    assert state.blocked_topics == ["sports"]


# source affinity ------------------------------------------------------------------------------


def test_source_affinity_rises_with_opens_and_falls_with_skips() -> None:
    state = LearnerState()
    batch = [pair(1.0, source="good") for _ in range(4)] + [
        pair(-0.6, source="bad") for _ in range(4)
    ]
    changes = update_sources(state, batch, CFG)
    assert state.source_affinity["good"] == pytest.approx(4 / (4 + CFG.affinity_prior))
    assert state.source_affinity["bad"] == pytest.approx(-4 / (4 + CFG.affinity_prior))
    assert {c.key for c in changes} == {"good", "bad"}


def test_source_affinity_stays_within_plus_minus_one() -> None:
    state = LearnerState()
    update_sources(state, [pair(1.0, source="s") for _ in range(500)], CFG)
    assert 0.9 < state.source_affinity["s"] < 1.0


def test_source_affinity_accumulates_across_runs_and_needs_evidence() -> None:
    state = LearnerState()
    update_sources(state, [pair(1.0, source="s")], CFG)
    first = state.source_affinity["s"]
    update_sources(state, [pair(1.0, source="s")], CFG)
    assert state.source_affinity["s"] > first
    assert first < 0.5  # a single open is not a verdict


def test_weak_signals_and_unknown_sources_do_not_move_affinity() -> None:
    state = LearnerState(source_affinity={"s": 0.3})
    assert update_sources(state, [pair(0.1, source="s"), pair(1.0, source=None)], CFG) == []
    assert state.source_affinity == {"s": 0.3}


# explore --------------------------------------------------------------------------------------


def test_engaged_explore_topic_graduates_into_the_profile() -> None:
    state = LearnerState(topics={"ai": 0.9})
    batch = [pair(1.0, topics={"culture": 0.9, "ai": 0.2}, explore=True)]
    (change,) = tune_explore(state, batch, CFG)
    assert (change.kind, change.key) == ("explore_graduated", "culture")
    assert state.topics["culture"] == CFG.explore_graduate_weight


def test_graduation_never_lowers_a_stronger_topic() -> None:
    state = LearnerState(topics={"culture": 0.8})
    assert tune_explore(state, [pair(1.0, topics={"culture": 0.9}, explore=True)], CFG) == []
    assert state.topics["culture"] == 0.8


def test_ignored_explore_lowers_the_rate() -> None:
    state = LearnerState()
    batch = [pair(-0.05, topics={"culture": 0.9}, explore=True) for _ in range(3)]
    (change,) = tune_explore(state, batch, CFG, base_rate=0.15)
    assert change.kind == "explore_rate"
    assert state.explore_rate == pytest.approx(0.15 * CFG.explore_decay)


def test_explore_rate_never_drops_below_five_percent() -> None:
    state = LearnerState(explore_rate=0.051)
    batch = [pair(-0.6, explore=True) for _ in range(4)]
    tune_explore(state, batch, CFG)
    assert state.explore_rate == 0.05
    assert tune_explore(state, batch, CFG) == []  # already at the floor
    assert state.explore_rate == 0.05


def test_engaged_explore_keeps_the_rate() -> None:
    state = LearnerState()
    batch = [pair(1.0, topics={"culture": 0.9}, explore=True), pair(-0.05, explore=True)]
    tune_explore(state, [*batch, pair(-0.05, explore=True)], CFG)
    assert state.explore_rate is None


def test_a_few_ignored_explore_picks_are_not_enough_to_judge() -> None:
    state = LearnerState()
    assert tune_explore(state, [pair(-0.05, explore=True) for _ in range(2)], CFG) == []


# the whole update -----------------------------------------------------------------------------


def test_learn_returns_a_new_state_and_leaves_the_input_alone() -> None:
    state = LearnerState(topics={"ai": 0.5}, interest_vector=[1.0, 0.0])
    new, changes = learn(state, [pair(1.0, topics={"ai": 1.0}, embedding=[0.0, 1.0])], CFG)
    assert state.topics == {"ai": 0.5}
    assert state.interest_vector == [1.0, 0.0]
    assert new.topics["ai"] > 0.5
    assert {c.kind for c in changes} >= {"topic_weight", "interest_vector"}


def test_learn_with_no_signals_only_decays() -> None:
    state = LearnerState(topics={"ai": 0.5})
    new, changes = learn(state, [], CFG)
    assert [c.kind for c in changes] == ["topic_decay"]
    assert new.topics["ai"] < 0.5
    _, incremental = learn(state, [], CFG, nightly=False)
    assert incremental == []
