"""Glue between the learner's state and ranking's ProfileView, for tests."""

from dataclasses import replace

from app.personalize.learn import LearnerState
from app.personalize.types import ProfileView


def view_from(base: ProfileView, state: LearnerState) -> ProfileView:
    return replace(
        base,
        topics=dict(state.topics),
        entities={k: list(v) for k, v in state.entities.items()},
        learned_entities={k: list(v) for k, v in state.learned_entities.items()},
        blocked_topics=frozenset(state.blocked_topics),
        source_affinity=dict(state.source_affinity),
        interest_vector=state.interest_vector,
        explore_rate=state.explore_rate,
    )
