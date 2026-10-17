import pytest

from app.onboarding.profile_builder import (
    BuilderInput,
    TasteAnswer,
    build_profile,
    topic_weights,
    weighted_mean,
)
from app.schemas.onboarding import ParsedBlocked, ParsedEntities, ParsedInterests, ParsedTopic

PARSED = ParsedInterests(
    topics=[ParsedTopic(slug="ai", weight=0.9), ParsedTopic(slug="f1", weight=0.6)],
    keywords=["AI agents", "ai agents", "PSL", "gossip"],
    entities=ParsedEntities(teams=["Lahore Qalandars"]),
    blocked=ParsedBlocked(topics=["film-tv"], keywords=["Gossip"]),
    context="Runs a digital agency.",
)


def liked(*topics: str, vector: list[float] | None = None) -> TasteAnswer:
    return TasteAnswer(dict.fromkeys(topics, 0.8), vector, liked=True)


def skipped(*topics: str) -> TasteAnswer:
    return TasteAnswer(dict.fromkeys(topics, 0.8), [9.0, 9.0], liked=False)


def test_explicit_picks_alone_are_equal() -> None:
    weights = topic_weights(BuilderInput(explicit_topics=["ai", "cricket", "f1"]))
    assert weights == {"ai": 1.0, "cricket": 1.0, "f1": 1.0}


def test_weights_add_explicit_text_and_taste_then_scale_to_the_top() -> None:
    inp = BuilderInput(
        explicit_topics=["ai", "cricket", "f1"],
        parsed=PARSED,
        taste=[liked("cricket"), liked("cricket"), skipped("f1")],
    )
    # raw: ai 0.8+0.9=1.7, cricket 0.8+0.1+0.1=1.0, f1 0.8+0.6-0.1=1.3
    assert topic_weights(inp) == {
        "ai": 1.0,
        "f1": pytest.approx(1.3 / 1.7, abs=1e-4),
        "cricket": pytest.approx(1.0 / 1.7, abs=1e-4),
    }


def test_taste_can_introduce_a_topic_outside_the_picks() -> None:
    inp = BuilderInput(explicit_topics=["ai", "cricket", "f1"], taste=[liked("space")])
    weights = topic_weights(inp)
    assert weights["space"] == pytest.approx(0.1 / 0.8, abs=1e-4)
    assert weights["ai"] == 1.0


def test_skips_can_remove_a_topic_and_blocks_always_do() -> None:
    inp = BuilderInput(
        explicit_topics=["ai", "cricket", "film-tv"],
        parsed=PARSED,
        taste=[skipped("space"), skipped("space")],
    )
    weights = topic_weights(inp)
    assert "space" not in weights
    assert "film-tv" not in weights  # blocked in the reader's own words


def test_no_signal_no_weights() -> None:
    assert topic_weights(BuilderInput(explicit_topics=[])) == {}


def test_profile_fields() -> None:
    inp = BuilderInput(
        explicit_topics=["ai", "cricket", "f1"],
        deeper={"cricket": ["PSL", "Test cricket"], "ai": ["Gossip"]},
        parsed=PARSED,
    )
    built = build_profile(inp)
    assert built.keywords == ["AI agents", "PSL", "Test cricket"]  # deduped; blocked removed
    assert built.entities["teams"] == ["Lahore Qalandars"]
    assert built.blocked == {"topics": ["film-tv"], "keywords": ["Gossip"], "sources": []}
    assert built.context_notes == "Runs a digital agency."


def test_context_falls_back_to_the_readers_text() -> None:
    built = build_profile(BuilderInput(explicit_topics=["ai"], raw_text="  I run a bakery  "))
    assert built.context_notes == "I run a bakery"
    assert build_profile(BuilderInput(explicit_topics=["ai"])).context_notes is None


def test_interest_vector_is_the_weighted_mean_of_stored_vectors() -> None:
    inp = BuilderInput(
        explicit_topics=["ai", "cricket", "f1"],
        parsed=PARSED,
        taste=[liked("ai", vector=[0.0, 1.0]), skipped("cricket")],
        prototypes={"ai": [1.0, 0.0], "cricket": [0.0, 1.0], "other": [5.0, 5.0]},
        keyword_vectors=[[1.0, 1.0]],
    )
    built = build_profile(inp)
    weights = built.topics  # ai 1.0, f1 ..., cricket ...; f1 has no prototype
    parts = [
        (weights["ai"], [1.0, 0.0]),
        (weights["cricket"], [0.0, 1.0]),
        (0.5, [0.0, 1.0]),
        (0.4, [1.0, 1.0]),
    ]
    assert built.interest_vector == pytest.approx(weighted_mean(parts))


def test_vector_is_deterministic_and_none_without_vectors() -> None:
    inp = BuilderInput(explicit_topics=["ai", "cricket", "f1"], prototypes={"ai": [1.0, 2.0]})
    assert build_profile(inp) == build_profile(inp)
    assert build_profile(BuilderInput(explicit_topics=["ai"])).interest_vector is None
    assert weighted_mean([]) is None


def test_skipped_stories_do_not_enter_the_vector() -> None:
    inp = BuilderInput(explicit_topics=["ai"], taste=[skipped("ai")])
    assert build_profile(inp).interest_vector is None
