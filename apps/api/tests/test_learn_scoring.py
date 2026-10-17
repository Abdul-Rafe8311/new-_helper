"""What the learner writes is what Task 8's scoring reads."""

from dataclasses import replace
from uuid import uuid4

import pytest

from app.personalize.learn import LearnerState, StoryFacts, learn
from app.personalize.score import score_candidate
from app.personalize.signals import StorySignal
from tests.learn_helpers import view_from
from tests.personalize_helpers import NOW, candidate, profile


def test_learned_source_affinity_scales_the_score() -> None:
    source = uuid4()
    c = candidate(source_id=source, topics={"ai": 0.9})
    base_view = profile(topics={"ai": 0.8})
    state = LearnerState(topics={"ai": 0.8})
    sig = StorySignal(c.id, c.id, 1.0, {"open": 1.0}, NOW)
    facts = StoryFacts(c.id, c.topics, c.entities, None, str(source))
    new, _ = learn(state, [(sig, facts)] * 4)

    learned_view = replace(base_view, source_affinity=new.source_affinity)
    before = score_candidate(c, base_view, NOW)
    after = score_candidate(c, learned_view, NOW)

    assert after.breakdown["multiplier"] > before.breakdown["multiplier"] == 1.0
    assert after.score > before.score


def test_learned_entity_starts_matching_stories() -> None:
    ada = {"people": ["Ada Lovelace"]}
    c = candidate(entities=ada)
    state = LearnerState(entities={"people": []})
    sig = StorySignal(c.id, c.id, 1.0, {"open": 1.0}, NOW)
    facts = StoryFacts(c.id, {}, ada, None, None)
    new, _ = learn(state, [(sig, facts)] * 3)

    plain = profile()
    learned = view_from(plain, new)
    assert score_candidate(c, plain, NOW).breakdown["raw"]["match"] == 0.0
    assert score_candidate(c, learned, NOW).breakdown["raw"]["match"] == pytest.approx(0.5)
    assert score_candidate(c, learned, NOW).breakdown["terms"] == ["Ada Lovelace"]


def test_learned_interest_vector_raises_the_semantic_component() -> None:
    c = candidate(embedding=[0.0, 1.0])
    state = LearnerState(interest_vector=[1.0, 0.0])
    sig = StorySignal(c.id, c.id, 1.0, {"open": 1.0}, NOW)
    facts = StoryFacts(c.id, {}, {}, [0.0, 1.0], None)
    new, _ = learn(state, [(sig, facts)] * 3)

    before = score_candidate(c, profile(interest_vector=[1.0, 0.0]), NOW)
    after = score_candidate(c, profile(interest_vector=new.interest_vector), NOW)
    assert after.breakdown["raw"]["semantic"] > before.breakdown["raw"]["semantic"]
