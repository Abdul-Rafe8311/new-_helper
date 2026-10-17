"""Story clustering: near-duplicate articles from the last 36 hours share a cluster_id."""

from collections.abc import Iterable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Article

WINDOW = timedelta(hours=36)
SIMILARITY = 0.86  # cosine; pgvector's <=> is the distance, 1 - cosine


class UnionFind[T]:
    def __init__(self, items: Iterable[T]) -> None:
        self._parent = {i: i for i in items}

    def find(self, x: T) -> T:
        root = x
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[x] != root:  # path compression
            self._parent[x], x = root, self._parent[x]
        return root

    def union(self, a: T, b: T) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[rb] = ra

    def groups(self) -> list[list[T]]:
        out: dict[T, list[T]] = {}
        for item in self._parent:
            out.setdefault(self.find(item), []).append(item)
        return list(out.values())


class Candidate(Protocol):
    @property
    def quality(self) -> float:
        """Source quality, 0..1."""

    @property
    def length(self) -> int:
        """Length of the article text."""


def representative[C: Candidate](members: Sequence[C]) -> C:
    """Highest source quality first, then the longest text."""
    return max(members, key=lambda m: (m.quality, m.length))


def assign_cluster_ids(
    ids: Sequence[UUID], pairs: Iterable[tuple[UUID, UUID]], first_id: int
) -> dict[UUID, tuple[int, int]]:
    """Union linked pairs; returns {article: (cluster_id, cluster_size)}. Singletons get one too."""
    uf = UnionFind(ids)
    for a, b in pairs:
        uf.union(a, b)
    out: dict[UUID, tuple[int, int]] = {}
    for cid, members in enumerate(sorted(uf.groups(), key=lambda g: str(min(g))), start=first_id):
        for m in members:
            out[m] = (cid, len(members))
    return out


ARTICLE_TIME = func.coalesce(Article.published_at, Article.fetched_at, Article.created_at)


async def cluster_recent(
    session: AsyncSession,
    *,
    now: datetime | None = None,
    threshold: float = SIMILARITY,
) -> dict[str, int]:
    """Recompute clusters for embedded articles in the window. Returns counts."""
    cutoff = (now or datetime.now(UTC)) - WINDOW
    window = [Article.embedding.is_not(None), cutoff <= ARTICLE_TIME]
    ids = list((await session.scalars(select(Article.id).where(*window))).all())
    if not ids:
        return {"articles": 0, "clusters": 0, "multi_article_clusters": 0}

    # cluster ids of articles outside the window stay untouched; new ones start above them
    base = await session.scalar(
        select(func.coalesce(func.max(Article.cluster_id), 0)).where(
            Article.id.not_in(ids), Article.cluster_id.is_not(None)
        )
    )
    pairs = (
        await session.execute(
            text(
                """
                SELECT a.id, b.id FROM articles a
                JOIN articles b ON a.id < b.id
                WHERE a.id = ANY(:ids) AND b.id = ANY(:ids)
                  AND a.embedding <=> b.embedding <= :max_distance
                """
            ),
            {"ids": ids, "max_distance": 1 - threshold},
        )
    ).all()
    assignment = assign_cluster_ids(ids, [(a, b) for a, b in pairs], (base or 0) + 1)
    for (cid, size), group in _group_by_value(assignment).items():
        await session.execute(
            update(Article).where(Article.id.in_(group)).values(cluster_id=cid, cluster_size=size)
        )
    await session.commit()
    sizes = {cid for cid, _ in assignment.values()}
    multi = {cid for cid, size in assignment.values() if size > 1}
    return {"articles": len(ids), "clusters": len(sizes), "multi_article_clusters": len(multi)}


def _group_by_value(
    assignment: dict[UUID, tuple[int, int]],
) -> dict[tuple[int, int], list[UUID]]:
    out: dict[tuple[int, int], list[UUID]] = {}
    for article_id, key in assignment.items():
        out.setdefault(key, []).append(article_id)
    return out
