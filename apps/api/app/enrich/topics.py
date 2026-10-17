"""Topic tagging with embeddings only: cosine against stored taxonomy prototypes."""

from collections.abc import Mapping, Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embedder import Embedder, cosine
from app.core.taxonomy import TOPICS
from app.models.ai import TopicPrototype

MAX_TOPICS = 3
MIN_SCORE = 0.55  # blended score an article needs for a topic
SOURCE_PRIOR_WEIGHT = 0.2  # share of the score that comes from the source's own topics


def tag_topics(
    embedding: Sequence[float],
    prototypes: Mapping[str, Sequence[float]],
    source_topics: Sequence[str] = (),
    *,
    min_score: float = MIN_SCORE,
    prior_weight: float = SOURCE_PRIOR_WEIGHT,
) -> dict[str, float]:
    """Top 3 topics as {slug: score}; cosine similarity blended with the source prior."""
    prior = set(source_topics)
    scored = {
        slug: (1 - prior_weight) * cosine(embedding, proto)
        + (prior_weight if slug in prior else 0.0)
        for slug, proto in prototypes.items()
    }
    best = sorted(scored.items(), key=lambda kv: kv[1], reverse=True)[:MAX_TOPICS]
    return {slug: round(score, 4) for slug, score in best if score >= min_score}


async def ensure_prototypes(session: AsyncSession, embedder: Embedder) -> int:
    """Embed taxonomy descriptions that are new or changed. Returns how many were written."""
    rows = await session.execute(select(TopicPrototype.slug, TopicPrototype.description))
    existing = dict(rows.all())
    stale = [t for t in TOPICS if existing.get(t.slug) != t.description]
    if not stale:
        return 0
    vectors = embedder.embed([f"{t.label}. {t.description}" for t in stale])
    stmt = insert(TopicPrototype).values(
        [
            {"slug": t.slug, "description": t.description, "embedding": v}
            for t, v in zip(stale, vectors, strict=True)
        ]
    )
    await session.execute(
        stmt.on_conflict_do_update(
            index_elements=["slug"],
            set_={"description": stmt.excluded.description, "embedding": stmt.excluded.embedding},
        )
    )
    await session.commit()
    return len(stale)


async def load_prototypes(session: AsyncSession) -> dict[str, list[float]]:
    rows = await session.execute(select(TopicPrototype.slug, TopicPrototype.embedding))
    return {slug: [float(x) for x in emb] for slug, emb in rows.all()}
