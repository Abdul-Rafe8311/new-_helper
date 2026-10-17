from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embedder import FakeEmbedder
from app.enrich.clusters import UnionFind, assign_cluster_ids, cluster_recent, representative
from tests.factories import make_article, make_source

E = FakeEmbedder()
NOW = datetime(2026, 10, 17, 6, 0, tzinfo=UTC)


def test_union_find_groups_transitively() -> None:
    uf = UnionFind(range(6))
    uf.union(0, 1)
    uf.union(1, 2)
    uf.union(4, 5)
    assert sorted(sorted(g) for g in uf.groups()) == [[0, 1, 2], [3], [4, 5]]


def test_assign_cluster_ids_includes_singletons_and_offsets() -> None:
    a, b, c = (UUID(int=i) for i in (1, 2, 3))
    out = assign_cluster_ids([a, b, c], [(a, b)], first_id=10)
    assert out[a] == out[b] == (10, 2)
    assert out[c] == (11, 1)


def test_representative_prefers_quality_then_length() -> None:
    low = SimpleNamespace(quality=0.5, length=9000)
    best = SimpleNamespace(quality=0.9, length=100)
    long_ = SimpleNamespace(quality=0.9, length=500)
    assert representative([low, best, long_]) is long_


@pytest.mark.integration
async def test_cluster_recent_links_similar_articles_only(db: AsyncSession) -> None:
    src = await make_source(db)
    texts = {
        "a": "central bank raises interest rates inflation worries markets",
        "b": "central bank raises interest rates inflation worries markets again",
        "c": "cricket team wins the final match in dramatic style",
        "old": "central bank raises interest rates inflation worries markets",
    }
    vecs = dict(zip(texts, E.embed(list(texts.values())), strict=True))
    arts = {}
    for key in texts:
        arts[key] = await make_article(
            db,
            source_id=src.id,
            title=key,
            embedding=vecs[key],
            published_at=NOW - timedelta(hours=60 if key == "old" else 2),
        )
    stats = await cluster_recent(db, now=NOW, threshold=0.86)
    await db.refresh(arts["a"])
    for a in arts.values():
        await db.refresh(a)
    assert stats == {"articles": 3, "clusters": 2, "multi_article_clusters": 1}
    assert arts["a"].cluster_id == arts["b"].cluster_id
    assert arts["a"].cluster_size == 2
    assert arts["c"].cluster_id != arts["a"].cluster_id
    assert arts["c"].cluster_size == 1
    assert arts["old"].cluster_id is None  # outside the 36h window


@pytest.mark.integration
async def test_cluster_ids_do_not_collide_with_older_clusters(db: AsyncSession) -> None:
    await make_article(
        db, title="old", cluster_id=7, cluster_size=1, published_at=NOW - timedelta(days=5)
    )
    fresh = await make_article(db, title="x", embedding=E.embed(["x"])[0], published_at=NOW)
    await cluster_recent(db, now=NOW)
    await db.refresh(fresh)
    assert fresh.cluster_id == 8
