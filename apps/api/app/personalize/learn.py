"""The profile updater: how a reader's profile moves in response to what they did.

`learn()` is pure. It takes the profile as it stands, the day's `StorySignal`s paired with what
we know about each story, and returns the new profile plus a `Change` for every move it made.
The database layer (`learn_service`) loads and stores; nothing here touches I/O.

Rules, in the order they are applied:
  1. topic weights   EMA towards the signal-weighted share of positive evidence per topic;
                     topics that got no signal at all decay slowly.
  2. interest vector Rocchio: v' = normalise(a v + b mean(liked) - c mean(disliked)).
  3. entities        named in >= N liked stories -> promoted into the profile (learned).
  4. blocking        a topic that keeps getting "less like this" is blocked.
  5. source affinity opens against skips per source, smoothed, in [-1, 1].
  6. explore         engaged explore topics graduate into the profile; ignored explore slots
                     lower the explore rate towards a floor.
"""

import math
from collections import defaultdict
from collections.abc import Iterable, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.personalize.config import DEFAULT_LEARNING, DEFAULT_SELECTION, LearningConfig
from app.personalize.signals import StorySignal

ENTITY_KINDS = ("people", "companies", "teams", "places")
MIN_TOPIC_MOVE = 1e-4
MIN_AFFINITY_MOVE = 1e-3


@dataclass(frozen=True, slots=True)
class StoryFacts:
    """What the learner knows about a story, copied out of the article row."""

    article_id: UUID
    topics: dict[str, float]
    entities: dict[str, list[str]]
    embedding: list[float] | None
    source_id: str | None
    explore: bool = False

    @property
    def lead_topic(self) -> str | None:
        return max(self.topics, key=lambda t: (self.topics[t], t), default=None)


@dataclass(slots=True)
class LearnerState:
    """The slice of a reader's profile that learning reads and writes."""

    topics: dict[str, float] = field(default_factory=dict)
    interest_vector: list[float] | None = None
    entities: dict[str, list[str]] = field(default_factory=dict)
    learned_entities: dict[str, list[str]] = field(default_factory=dict)
    blocked_topics: list[str] = field(default_factory=list)
    source_affinity: dict[str, float] = field(default_factory=dict)
    explore_rate: float | None = None
    # running tallies that make the rules incremental (persisted in reader_profiles.learn_state)
    entity_counts: dict[str, int] = field(default_factory=dict)
    less_like_counts: dict[str, int] = field(default_factory=dict)
    source_stats: dict[str, dict[str, int]] = field(default_factory=dict)

    def copy(self) -> "LearnerState":
        return deepcopy(self)


@dataclass(frozen=True, slots=True)
class Change:
    """One thing that moved, for the ProfileChange log."""

    kind: str
    key: str | None
    before: Any
    after: Any
    delta: float | None
    reason: str
    signals: list[dict[str, Any]]


Pair = tuple[StorySignal, StoryFacts]


def _round(x: float) -> float:
    return round(x, 6)


def top_signals(pairs: Iterable[tuple[Pair, float]], limit: int = 3) -> list[dict[str, Any]]:
    """The events that contributed most, as small JSON-able dicts."""
    ranked = sorted(pairs, key=lambda p: abs(p[1]), reverse=True)[:limit]
    out: list[dict[str, Any]] = []
    for (sig, _), contribution in ranked:
        lead = max(sig.parts, key=lambda k: abs(sig.parts[k]))
        out.append(
            {"type": lead, "article_id": str(sig.article_id), "weight": _round(contribution)}
        )
    return out


def liked(pairs: Sequence[Pair], cfg: LearningConfig) -> list[Pair]:
    return [p for p in pairs if p[0].weight >= cfg.positive_threshold]


def disliked(pairs: Sequence[Pair], cfg: LearningConfig) -> list[Pair]:
    return [p for p in pairs if p[0].weight <= cfg.negative_threshold]


# 1. topics -----------------------------------------------------------------------------------


def update_topics(
    state: LearnerState, pairs: Sequence[Pair], cfg: LearningConfig, *, idle_decay: bool
) -> list[Change]:
    pos: dict[str, float] = defaultdict(float)
    neg: dict[str, float] = defaultdict(float)
    contributions: dict[str, list[tuple[Pair, float]]] = defaultdict(list)
    for pair in pairs:
        sig, facts = pair
        for topic, score in facts.topics.items():
            evidence = sig.weight * score
            (pos if evidence > 0 else neg)[topic] += abs(evidence)
            contributions[topic].append((pair, evidence))

    changes: list[Change] = []
    for topic in sorted(contributions):
        mass = pos[topic] + neg[topic]
        if mass == 0.0:
            continue
        target = pos[topic] / mass
        confidence = mass / (mass + cfg.topic_confidence_mass)
        before = state.topics.get(topic, 0.0)
        after = min(1.0, max(0.0, before + cfg.topic_alpha * confidence * (target - before)))
        if abs(after - before) < MIN_TOPIC_MOVE:
            continue
        state.topics[topic] = after
        direction = "positive" if after > before else "negative"
        changes.append(
            Change(
                "topic_weight",
                topic,
                _round(before),
                _round(after),
                _round(after - before),
                f"{direction} evidence (target {target:.2f}, confidence {confidence:.2f})",
                top_signals(contributions[topic]),
            )
        )

    if idle_decay:
        before_all = {t: w for t, w in state.topics.items() if t not in contributions and w > 0}
        if before_all:
            after_all = {t: w * cfg.topic_idle_decay for t, w in before_all.items()}
            state.topics.update(after_all)
            changes.append(
                Change(
                    "topic_decay",
                    None,
                    {t: _round(w) for t, w in before_all.items()},
                    {t: _round(w) for t, w in after_all.items()},
                    _round(sum(after_all.values()) - sum(before_all.values())),
                    f"no signal on {len(before_all)} topics; weights x {cfg.topic_idle_decay}",
                    [],
                )
            )
    return changes


# 2. interest vector --------------------------------------------------------------------------


def _mean(vectors: Sequence[list[float]]) -> list[float]:
    dim = len(vectors[0])
    return [sum(v[i] for v in vectors) / len(vectors) for i in range(dim)]


def _normalise(v: list[float]) -> list[float] | None:
    norm = math.sqrt(sum(x * x for x in v))
    return [x / norm for x in v] if norm > 0 else None


def rocchio(
    current: list[float] | None,
    positive: Sequence[list[float]],
    negative: Sequence[list[float]],
    cfg: LearningConfig = DEFAULT_LEARNING,
) -> list[float] | None:
    """v' = normalise(a v + b mean(positive) - c mean(negative)); `current` when nothing moves."""
    if not positive and not negative:
        return current
    dim = len((positive or negative)[0])
    new = [cfg.rocchio_alpha * x for x in current] if current else [0.0] * dim
    if positive:
        new = [a + cfg.rocchio_beta * b for a, b in zip(new, _mean(positive), strict=True)]
    if negative:
        new = [a - cfg.rocchio_gamma * b for a, b in zip(new, _mean(negative), strict=True)]
    return _normalise(new) or current


def update_vector(state: LearnerState, pairs: Sequence[Pair], cfg: LearningConfig) -> list[Change]:
    likes = [p for p in liked(pairs, cfg) if p[1].embedding]
    dislikes = [p for p in disliked(pairs, cfg) if p[1].embedding]
    new = rocchio(
        state.interest_vector,
        [p[1].embedding for p in likes if p[1].embedding],
        [p[1].embedding for p in dislikes if p[1].embedding],
        cfg,
    )
    if new is None or new == state.interest_vector:
        return []
    old = state.interest_vector
    state.interest_vector = new
    moved = None
    if old:
        dot = sum(a * b for a, b in zip(old, new, strict=True))
        moved = _round(1.0 - dot / (math.sqrt(sum(a * a for a in old)) or 1.0))
    return [
        Change(
            "interest_vector",
            None,
            None,
            None,
            moved,
            f"Rocchio step from {len(likes)} liked and {len(dislikes)} disliked stories",
            top_signals([(p, p[0].weight) for p in likes + dislikes]),
        )
    ]


# 3. entities ---------------------------------------------------------------------------------


def promote_entities(
    state: LearnerState, pairs: Sequence[Pair], cfg: LearningConfig
) -> list[Change]:
    """Count each entity once per liked story; promote at `entity_promote_after` stories."""
    known = {n.lower() for names in state.entities.values() for n in names}
    seen_in: dict[str, list[Pair]] = defaultdict(list)
    for pair in liked(pairs, cfg):
        names = {
            (kind, name.strip())
            for kind in ENTITY_KINDS
            for name in pair[1].entities.get(kind, [])
            if name.strip()
        }
        for kind, name in names:
            key = f"{kind}|{name}"
            state.entity_counts[key] = state.entity_counts.get(key, 0) + 1
            seen_in[key].append(pair)

    changes: list[Change] = []
    for key in sorted(seen_in):
        kind, name = key.split("|", 1)
        if state.entity_counts[key] < cfg.entity_promote_after or name.lower() in known:
            continue
        known.add(name.lower())
        state.entities.setdefault(kind, []).append(name)
        state.learned_entities.setdefault(kind, []).append(name)
        changes.append(
            Change(
                "entity_promoted",
                name,
                None,
                kind,
                None,
                f"named in {state.entity_counts[key]} stories the reader engaged with",
                top_signals([(p, p[0].weight) for p in seen_in[key]]),
            )
        )
    return changes


# 4. blocking ---------------------------------------------------------------------------------


def block_topics(state: LearnerState, pairs: Sequence[Pair], cfg: LearningConfig) -> list[Change]:
    hits: dict[str, list[Pair]] = defaultdict(list)
    for pair in pairs:
        topic = pair[1].lead_topic
        if topic and "less_like" in pair[0].parts:
            hits[topic].append(pair)
    changes: list[Change] = []
    for topic in sorted(hits):
        state.less_like_counts[topic] = state.less_like_counts.get(topic, 0) + len(hits[topic])
        if state.less_like_counts[topic] >= cfg.block_topic_after_less_likes and (
            topic not in state.blocked_topics
        ):
            state.blocked_topics.append(topic)
            changes.append(
                Change(
                    "topic_blocked",
                    topic,
                    False,
                    True,
                    None,
                    f"'less like this' on {state.less_like_counts[topic]} {topic} stories",
                    top_signals([(p, p[0].weight) for p in hits[topic]]),
                )
            )
    return changes


# 5. source affinity --------------------------------------------------------------------------


def update_sources(state: LearnerState, pairs: Sequence[Pair], cfg: LearningConfig) -> list[Change]:
    touched: dict[str, list[Pair]] = defaultdict(list)
    for pair in pairs:
        sid = pair[1].source_id
        if sid is None:
            continue
        sig = pair[0]
        if sig.weight >= cfg.positive_threshold:
            state.source_stats.setdefault(sid, {"pos": 0, "neg": 0})["pos"] += 1
            touched[sid].append(pair)
        elif sig.weight <= cfg.negative_threshold:
            state.source_stats.setdefault(sid, {"pos": 0, "neg": 0})["neg"] += 1
            touched[sid].append(pair)

    changes: list[Change] = []
    for sid in sorted(touched):
        stats = state.source_stats[sid]
        after = (stats["pos"] - stats["neg"]) / (stats["pos"] + stats["neg"] + cfg.affinity_prior)
        before = state.source_affinity.get(sid, 0.0)
        if abs(after - before) < MIN_AFFINITY_MOVE:
            continue
        state.source_affinity[sid] = after
        changes.append(
            Change(
                "source_affinity",
                sid,
                _round(before),
                _round(after),
                _round(after - before),
                f"{stats['pos']} opened vs {stats['neg']} skipped",
                top_signals([(p, p[0].weight) for p in touched[sid]]),
            )
        )
    return changes


# 6. explore ----------------------------------------------------------------------------------


def tune_explore(
    state: LearnerState,
    pairs: Sequence[Pair],
    cfg: LearningConfig,
    base_rate: float = DEFAULT_SELECTION.explore_share,
) -> list[Change]:
    shown = [p for p in pairs if p[1].explore]
    if not shown:
        return []
    engaged = [p for p in shown if p[0].weight >= cfg.positive_threshold]
    changes: list[Change] = []

    for pair in engaged:
        topic = pair[1].lead_topic
        before = state.topics.get(topic, 0.0) if topic else 0.0
        if topic and before < cfg.explore_graduate_weight:
            state.topics[topic] = cfg.explore_graduate_weight
            changes.append(
                Change(
                    "explore_graduated",
                    topic,
                    _round(before),
                    cfg.explore_graduate_weight,
                    _round(cfg.explore_graduate_weight - before),
                    "the reader engaged with an explore pick",
                    top_signals([(pair, pair[0].weight)]),
                )
            )

    share = len(engaged) / len(shown)
    if len(shown) >= cfg.explore_ignored_min_shown and share < cfg.explore_engaged_min_share:
        before_rate = state.explore_rate if state.explore_rate is not None else base_rate
        after_rate = max(cfg.explore_floor, before_rate * cfg.explore_decay)
        if after_rate < before_rate:
            state.explore_rate = after_rate
            changes.append(
                Change(
                    "explore_rate",
                    None,
                    _round(before_rate),
                    _round(after_rate),
                    _round(after_rate - before_rate),
                    f"{len(engaged)} of {len(shown)} explore picks engaged",
                    top_signals([(p, p[0].weight) for p in shown]),
                )
            )
    return changes


# the whole update ----------------------------------------------------------------------------


def learn(
    state: LearnerState,
    pairs: Sequence[Pair],
    cfg: LearningConfig = DEFAULT_LEARNING,
    *,
    nightly: bool = True,
    base_explore_rate: float = DEFAULT_SELECTION.explore_share,
) -> tuple[LearnerState, list[Change]]:
    """Apply every rule; returns a new state (the input is untouched) and the changes made.

    Incremental runs (`nightly=False`) skip the idle-topic decay so it happens once a day.
    """
    new = state.copy()
    changes: list[Change] = []
    changes += update_topics(new, pairs, cfg, idle_decay=nightly)
    changes += update_vector(new, pairs, cfg)
    changes += promote_entities(new, pairs, cfg)
    changes += block_topics(new, pairs, cfg)
    changes += update_sources(new, pairs, cfg)
    changes += tune_explore(new, pairs, cfg, base_explore_rate)
    return new, changes
