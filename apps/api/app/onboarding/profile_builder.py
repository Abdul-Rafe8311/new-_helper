"""Build a reader profile from everything onboarding captured. Pure and deterministic.

Topic weights are summed from three signals, then scaled so the strongest topic is 1.0:
  explicit picks  +0.8 each
  free text       +0.6 to 0.9 (the parsed weight)
  taste test      +0.1 per liked story, -0.1 per skipped one, on each topic the story carries
The interest vector is the weighted mean of stored vectors only (topic prototypes, liked
headlines, and articles matching the parsed keywords); nothing here loads a model.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from app.schemas.onboarding import ParsedBlocked, ParsedEntities, ParsedInterests

EXPLICIT_WEIGHT = 0.8
TASTE_DELTA = 0.1
LIKED_STORY_VECTOR_WEIGHT = 0.5
KEYWORD_VECTOR_WEIGHT = 0.4
MAX_KEYWORDS = 40


@dataclass(frozen=True, slots=True)
class TasteAnswer:
    topics: Mapping[str, float]  # the story's tagged topics
    embedding: Sequence[float] | None
    liked: bool


@dataclass(frozen=True, slots=True)
class BuilderInput:
    explicit_topics: Sequence[str]
    deeper: Mapping[str, Sequence[str]] = field(default_factory=dict)
    parsed: ParsedInterests | None = None
    raw_text: str = ""
    taste: Sequence[TasteAnswer] = ()
    prototypes: Mapping[str, Sequence[float]] = field(default_factory=dict)
    keyword_vectors: Sequence[Sequence[float]] = ()  # one mean vector per matched keyword


@dataclass(frozen=True, slots=True)
class BuiltProfile:
    topics: dict[str, float]
    keywords: list[str]
    entities: dict[str, list[str]]
    blocked: dict[str, list[str]]
    context_notes: str | None
    interest_vector: list[float] | None


def topic_weights(inp: BuilderInput) -> dict[str, float]:
    raw: dict[str, float] = {}
    for slug in inp.explicit_topics:
        raw[slug] = raw.get(slug, 0.0) + EXPLICIT_WEIGHT
    if inp.parsed is not None:
        for topic in inp.parsed.topics:
            raw[topic.slug] = raw.get(topic.slug, 0.0) + topic.weight
    for answer in inp.taste:
        delta = TASTE_DELTA if answer.liked else -TASTE_DELTA
        for slug in answer.topics:
            raw[slug] = raw.get(slug, 0.0) + delta

    blocked = set(inp.parsed.blocked.topics) if inp.parsed else set()
    positive = {s: w for s, w in raw.items() if w > 1e-9 and s not in blocked}
    if not positive:
        return {}
    top = max(positive.values())
    ranked = sorted(positive.items(), key=lambda kv: (-kv[1], kv[0]))
    return {slug: round(w / top, 4) for slug, w in ranked}


def _keywords(inp: BuilderInput) -> list[str]:
    candidates = list(inp.parsed.keywords) if inp.parsed else []
    candidates += [label for slug in inp.explicit_topics for label in inp.deeper.get(slug, ())]
    blocked = {k.casefold() for k in inp.parsed.blocked.keywords} if inp.parsed else set()
    out: dict[str, str] = {}
    for word in (c.strip() for c in candidates):
        if word and word.casefold() not in blocked:
            out.setdefault(word.casefold(), word)
    return list(out.values())[:MAX_KEYWORDS]


def weighted_mean(parts: Sequence[tuple[float, Sequence[float]]]) -> list[float] | None:
    total = sum(w for w, _ in parts)
    if not parts or total <= 0:
        return None
    dim = len(parts[0][1])
    acc = [0.0] * dim
    for weight, vector in parts:
        for i, x in enumerate(vector):
            acc[i] += weight * x
    return [x / total for x in acc]


def _interest_vector(inp: BuilderInput, weights: Mapping[str, float]) -> list[float] | None:
    parts: list[tuple[float, Sequence[float]]] = [
        (weight, inp.prototypes[slug]) for slug, weight in weights.items() if slug in inp.prototypes
    ]
    parts += [
        (LIKED_STORY_VECTOR_WEIGHT, a.embedding)
        for a in inp.taste
        if a.liked and a.embedding is not None
    ]
    parts += [(KEYWORD_VECTOR_WEIGHT, v) for v in inp.keyword_vectors]
    return weighted_mean(parts)


def build_profile(inp: BuilderInput) -> BuiltProfile:
    weights = topic_weights(inp)
    parsed = inp.parsed
    entities = (parsed.entities if parsed else ParsedEntities()).model_dump()
    blocked = parsed.blocked if parsed else ParsedBlocked()
    context = (parsed.context if parsed else "") or inp.raw_text
    return BuiltProfile(
        topics=weights,
        keywords=_keywords(inp),
        entities=entities,
        blocked={"topics": list(blocked.topics), "keywords": list(blocked.keywords), "sources": []},
        context_notes=context.strip()[:2000] or None,
        interest_vector=_interest_vector(inp, weights),
    )
