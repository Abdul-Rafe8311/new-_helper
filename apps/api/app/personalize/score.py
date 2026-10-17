"""Transparent weighted scoring.

score = (0.40 semantic + 0.20 topic + 0.15 match + 0.10 recency + 0.10 importance
         + 0.05 novelty) x source multiplier - penalties

Every component is in [0, 1]. The breakdown stores each weighted contribution, so any score
can be explained and the learning loop (T11) can be shown to move individual components.
"""

import math
import re
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from app.personalize.config import DEFAULT_SCORING, ScoringConfig
from app.personalize.types import Candidate, ProfileView, Scored

COMPONENTS = ("semantic", "topic", "match", "recency", "importance", "novelty")


def cosine(a: list[float], b: list[float]) -> float:
    dot = na = nb = 0.0
    for x, y in zip(a, b, strict=True):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / math.sqrt(na * nb)


def semantic_score(c: Candidate, profile: ProfileView) -> float:
    if c.embedding is None or profile.interest_vector is None:
        return 0.0
    return min(1.0, max(0.0, cosine(c.embedding, profile.interest_vector)))


def topic_affinity(c: Candidate, profile: ProfileView) -> tuple[float, str | None]:
    """Best article-topic score x profile weight over the article's topics, and that topic."""
    best, slug = 0.0, None
    for topic, score in c.topics.items():
        value = score * profile.topics.get(topic, 0.0)
        if value > best:
            best, slug = value, topic
    return min(1.0, best), slug


def _mentions(text: str, term: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text, flags=re.IGNORECASE) is not None


def matched_terms(c: Candidate, terms: Iterable[str]) -> list[str]:
    """Profile keywords/entities that the article names (in text or extracted entities)."""
    text = f"{c.title} {c.headline} {c.summary}"
    named = {e.lower() for group in c.entities.values() for e in group}
    return [t for t in terms if t.lower() in named or _mentions(text, t)]


def match_score(hits: int) -> float:
    """One hit is a strong signal, more hits saturate: 0, .5, .75, .875, ..."""
    return 1.0 - 0.5**hits


def recency_score(c: Candidate, now: datetime, half_life_hours: float) -> float:
    if c.published_at is None:
        return 0.5
    age_hours = max(0.0, (now - c.published_at).total_seconds() / 3600)
    return float(0.5 ** (age_hours / half_life_hours))


def importance_score(c: Candidate, saturation: int) -> float:
    """log(cluster size) scaled to saturate at `saturation` outlets, times source quality."""
    coverage = min(1.0, math.log(1 + c.cluster_size) / math.log(1 + saturation))
    return coverage * c.source_quality


def novelty_score(c: Candidate, profile: ProfileView) -> float:
    """How far the story sits from the reader's usual beats: 1 - strongest matching topic weight."""
    familiarity = max((profile.topics.get(t, 0.0) for t in c.topics), default=0.0)
    return 1.0 - min(1.0, familiarity)


def source_multiplier(c: Candidate, profile: ProfileView, spread: float) -> float:
    affinity = profile.source_affinity.get(str(c.source_id), 0.0) if c.source_id else 0.0
    return 1.0 + max(-1.0, min(1.0, float(affinity))) * spread


def score_candidate(
    c: Candidate,
    profile: ProfileView,
    now: datetime,
    cfg: ScoringConfig = DEFAULT_SCORING,
    seen_ids: frozenset[Any] = frozenset(),
) -> Scored:
    w = cfg.weights
    topic_value, topic_slug = topic_affinity(c, profile)
    terms = matched_terms(c, profile.terms)
    raw = {
        "semantic": semantic_score(c, profile),
        "topic": topic_value,
        "match": match_score(len(terms)),
        "recency": recency_score(c, now, cfg.recency_half_life_hours),
        "importance": importance_score(c, cfg.importance_saturation_size),
        "novelty": novelty_score(c, profile),
    }
    weighted = {name: round(raw[name] * getattr(w, name), 6) for name in COMPONENTS}
    multiplier = source_multiplier(c, profile, cfg.affinity_spread)
    penalties: dict[str, float] = {}
    if c.id in seen_ids:
        penalties["seen"] = cfg.seen_penalty
    if c.source_quality < cfg.low_quality_below:
        penalties["low_quality"] = cfg.low_quality_penalty
    total = max(0.0, sum(weighted.values()) * multiplier - sum(penalties.values()))
    breakdown: dict[str, Any] = {
        "components": weighted,
        "raw": {k: round(v, 6) for k, v in raw.items()},
        "multiplier": round(multiplier, 6),
        "penalties": penalties,
        "total": round(total, 6),
        "topic": topic_slug,
        "terms": terms[:3],
        "cluster_size": c.cluster_size,
        "origins": sorted(c.origins),
    }
    return Scored(candidate=c, score=total, breakdown=breakdown)


def score_all(
    candidates: Iterable[Candidate],
    profile: ProfileView,
    now: datetime,
    cfg: ScoringConfig = DEFAULT_SCORING,
    seen_ids: frozenset[Any] = frozenset(),
) -> list[Scored]:
    scored = [score_candidate(c, profile, now, cfg, seen_ids) for c in candidates]
    scored.sort(key=lambda s: (s.score, str(s.candidate.id)), reverse=True)
    return scored
