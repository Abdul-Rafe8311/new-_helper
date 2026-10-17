"""Taste-test headlines: real stories from today, diverse across the reader's topics.

`pick_headlines` is pure and deterministic; `load_candidates` reads the recent, already
enriched articles (stored topics and embeddings, no model loading).
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enrich.clusters import ARTICLE_TIME
from app.models.content import Article, Source
from app.onboarding.limits import TASTE_OUTSIDE, TASTE_TEST_SIZE

WINDOW = timedelta(hours=48)
MAX_CANDIDATES = 400
MAX_PER_SOURCE = 2
MIN_HEADLINE_CHARS = 15


@dataclass(frozen=True, slots=True)
class Candidate:
    id: UUID
    headline: str
    source: str
    image_url: str | None
    topics: dict[str, float]
    cluster_id: int | None
    quality: float
    published: datetime

    @property
    def primary_topic(self) -> str | None:
        return max(self.topics, key=lambda t: self.topics[t]) if self.topics else None


@dataclass(frozen=True, slots=True)
class Pick:
    candidate: Candidate
    topic: str | None
    outside: bool = field(default=False)


def _rank(c: Candidate) -> tuple[bool, float, datetime, str]:
    """Pictures first, then source quality, then freshness; the id breaks ties deterministically."""
    return (c.image_url is not None, c.quality, c.published, str(c.id))


def _usable(candidates: Sequence[Candidate]) -> list[Candidate]:
    """Best first; one story per cluster, a couple per source, no stubs."""
    seen_clusters: set[int] = set()
    per_source: dict[str, int] = {}
    out: list[Candidate] = []
    for c in sorted(candidates, key=_rank, reverse=True):
        if len(c.headline) < MIN_HEADLINE_CHARS:
            continue
        if c.cluster_id is not None and c.cluster_id in seen_clusters:
            continue
        if per_source.get(c.source, 0) >= MAX_PER_SOURCE:
            continue
        if c.cluster_id is not None:
            seen_clusters.add(c.cluster_id)
        per_source[c.source] = per_source.get(c.source, 0) + 1
        out.append(c)
    return out


def _round_robin(pools: list[list[Candidate]], limit: int) -> list[Candidate]:
    """Take the best from each pool in turn so no one topic dominates."""
    out: list[Candidate] = []
    queues = [list(p) for p in pools if p]
    while queues and len(out) < limit:
        for queue in list(queues):
            if len(out) >= limit:
                break
            out.append(queue.pop(0))
            if not queue:
                queues.remove(queue)
    return out


def _interleave(inside: list[Pick], outside: list[Pick]) -> list[Pick]:
    """Spread the outside picks through the deck instead of putting them at the end."""
    deck = list(inside)
    total = len(inside) + len(outside)
    slots = [round((i + 1) * total / (len(outside) + 1)) - 1 for i in range(len(outside))]
    for slot, pick in zip(slots, outside, strict=True):
        deck.insert(min(slot, len(deck)), pick)
    return deck


def pick_headlines(
    candidates: Sequence[Candidate],
    chosen_topics: Sequence[str],
    *,
    total: int = TASTE_TEST_SIZE,
    outside: int = TASTE_OUTSIDE,
) -> list[Pick]:
    """`total` headlines: mostly across the chosen topics, `outside` of them from elsewhere."""
    chosen = list(dict.fromkeys(chosen_topics))
    usable = _usable(candidates)
    inside_pools = [[c for c in usable if c.primary_topic == t] for t in chosen]
    outside_pool = [c for c in usable if c.primary_topic not in chosen and c.topics]
    # one pool per outside topic, so the outside picks differ from each other
    by_topic: dict[str, list[Candidate]] = {}
    for c in outside_pool:
        by_topic.setdefault(c.primary_topic or "", []).append(c)

    outside_picks = _round_robin(list(by_topic.values()), outside)
    inside_picks = _round_robin(inside_pools, total - len(outside_picks))
    taken = {c.id for c in [*outside_picks, *inside_picks]}

    # not enough on the chosen topics: top up from whatever is left, best first
    shortfall = total - len(outside_picks) - len(inside_picks)
    topup = [c for c in usable if c.id not in taken][:shortfall]
    inside_picks.extend(topup)

    # a top-up story from an unchosen topic is outside the bubble too
    inside_deck = [Pick(c, c.primary_topic, c.primary_topic not in chosen) for c in inside_picks]
    return _interleave(inside_deck, [Pick(c, c.primary_topic, outside=True) for c in outside_picks])


async def load_candidates(session: AsyncSession, now: datetime | None = None) -> list[Candidate]:
    since = (now or datetime.now(UTC)) - WINDOW
    rows = await session.execute(
        select(Article, Source.name, Source.quality)
        .join(Source, Article.source_id == Source.id)
        .where(since <= ARTICLE_TIME, Article.embedding.is_not(None), Article.topics != {})
        .order_by(ARTICLE_TIME.desc())
        .limit(MAX_CANDIDATES)
    )
    return [
        Candidate(
            id=a.id,
            headline=(a.headline or a.title).strip(),
            source=source_name,
            image_url=a.image_url,
            topics=a.topics,
            cluster_id=a.cluster_id,
            quality=quality,
            published=a.published_at or a.fetched_at or a.created_at,
        )
        for a, source_name, quality in rows.all()
    ]
