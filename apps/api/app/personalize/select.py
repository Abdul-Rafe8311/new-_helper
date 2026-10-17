"""Choose the paper's items from the scored pool.

1. Explore slots (when "surprise me" is on): ~15% of the paper goes to high-quality stories from
   outside the reader's strongest topics, so the paper never becomes an echo chamber.
2. The rest is picked greedily by MMR: lambda x relevance - (1 - lambda) x similarity to what is
   already chosen, with at most 2 items per source and 1 per story cluster.
"""

from dataclasses import dataclass
from uuid import UUID

from app.core.taxonomy import TOPICS_BY_SLUG
from app.personalize.config import DEFAULT_SELECTION, SelectionConfig, item_count
from app.personalize.score import cosine
from app.personalize.types import ProfileView, Scored

# explanation needs a human reason; below this weighted strength we fall back to the generic one
MIN_REASON_STRENGTH = 0.02
BIG_STORY_MIN_OUTLETS = 3


@dataclass(frozen=True, slots=True)
class Selection:
    scored: Scored
    explore: bool
    why: str


def topic_label(slug: str) -> str:
    topic = TOPICS_BY_SLUG.get(slug)
    return topic.label if topic else slug.replace("-", " ").title()


def why_text(item: Scored, *, explore: bool = False) -> str:
    """A short, honest reason taken from the strongest explainable score component."""
    b = item.breakdown
    if explore:
        label = b.get("topic")
        return "Outside your usual beats" + (f": {topic_label(label)}" if label else "")
    weighted = b["components"]
    options: list[tuple[float, str]] = []
    if b.get("terms"):
        options.append((weighted["match"], f"Because you follow {b['terms'][0]}"))
    if b.get("topic"):
        options.append((weighted["topic"], f"Because you follow {topic_label(b['topic'])}"))
    if b["cluster_size"] >= BIG_STORY_MIN_OUTLETS:
        options.append(
            (weighted["importance"], f"Big story: {b['cluster_size']} outlets covering it")
        )
    # max() keeps the first of equal values, so ties resolve match > topic > big story
    strength, reason = max(options, key=lambda o: o[0], default=(0.0, ""))
    return reason if strength >= MIN_REASON_STRENGTH else "Similar to what you like to read"


def _explore_rank(s: Scored) -> float:
    raw = s.breakdown["raw"]
    return float(0.5 * s.candidate.source_quality + 0.3 * raw["importance"] + 0.2 * raw["recency"])


def _is_outside(s: Scored, top_topics: set[str]) -> bool:
    leading = sorted(s.candidate.topics, key=lambda t: s.candidate.topics[t], reverse=True)[:2]
    return not top_topics.intersection(leading)


class _Picks:
    """Chosen items plus the per-source and per-cluster limits they impose."""

    def __init__(self, max_per_source: int) -> None:
        self.items: list[Scored] = []
        self._max = max_per_source
        self._sources: dict[UUID | None, int] = {}
        self._clusters: set[int] = set()

    def allows(self, s: Scored) -> bool:
        c = s.candidate
        if c.cluster_id is not None and c.cluster_id in self._clusters:
            return False
        return c.source_id is None or self._sources.get(c.source_id, 0) < self._max

    def add(self, s: Scored) -> None:
        self.items.append(s)
        c = s.candidate
        if c.cluster_id is not None:
            self._clusters.add(c.cluster_id)
        if c.source_id is not None:
            self._sources[c.source_id] = self._sources.get(c.source_id, 0) + 1

    def max_similarity(self, s: Scored) -> float:
        emb = s.candidate.embedding
        if emb is None:
            return 0.0
        sims = [cosine(emb, p.candidate.embedding) for p in self.items if p.candidate.embedding]
        return max(sims, default=0.0)


def explore_count(n: int, cfg: SelectionConfig, profile: ProfileView) -> int:
    if not profile.surprise_me:
        return 0
    share = profile.explore_rate if profile.explore_rate is not None else cfg.explore_share
    return round(n * share)


def select_items(
    scored: list[Scored],
    profile: ProfileView,
    cfg: SelectionConfig = DEFAULT_SELECTION,
) -> list[Selection]:
    """`scored` must be sorted best first (score_all does this)."""
    n = item_count(profile.reading_minutes)
    picks = _Picks(cfg.max_per_source)

    top = set(profile.top_topics(cfg.top_topic_count))
    explore_pool = sorted(
        (
            s
            for s in scored
            if s.candidate.source_quality >= cfg.explore_min_quality and _is_outside(s, top)
        ),
        key=lambda s: (_explore_rank(s), str(s.candidate.id)),
        reverse=True,
    )
    explore_ids: set[UUID] = set()
    for s in explore_pool:
        if len(explore_ids) >= min(explore_count(n, cfg, profile), n):
            break
        if picks.allows(s):
            picks.add(s)
            explore_ids.add(s.candidate.id)

    pool = [s for s in scored[: cfg.mmr_pool] if s.candidate.id not in explore_ids]
    top_score = max((s.score for s in pool), default=0.0) or 1.0
    while len(picks.items) < n:
        best: tuple[float, Scored] | None = None
        for s in pool:
            if not picks.allows(s):
                continue
            mmr = cfg.mmr_lambda * (s.score / top_score) - (1 - cfg.mmr_lambda) * (
                picks.max_similarity(s)
            )
            # ties resolve to the better raw score, then id, so runs are reproducible
            if best is None or (mmr, s.score, str(s.candidate.id)) > (
                best[0],
                best[1].score,
                str(best[1].candidate.id),
            ):
                best = (mmr, s)
        if best is None:
            break
        picks.add(best[1])
        pool.remove(best[1])

    main = [s for s in picks.items if s.candidate.id not in explore_ids]
    explore = [s for s in picks.items if s.candidate.id in explore_ids]
    return [Selection(s, False, why_text(s)) for s in main] + [
        Selection(s, True, why_text(s, explore=True)) for s in explore
    ]
