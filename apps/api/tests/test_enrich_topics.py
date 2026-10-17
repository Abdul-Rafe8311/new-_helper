import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embedder import FakeEmbedder
from app.core.catalogue import CATALOGUE
from app.enrich.topics import ensure_prototypes, load_prototypes, tag_topics

E = FakeEmbedder()
PROTOS = dict(
    zip(
        ["cricket", "markets", "space"],
        E.embed(["cricket test match wickets", "stock market shares", "rocket launch orbit"]),
        strict=True,
    )
)


def test_best_match_wins_and_unrelated_topics_are_dropped() -> None:
    (vec,) = E.embed(["cricket test match wickets"])
    tags = tag_topics(vec, PROTOS)
    assert list(tags) == ["cricket"]
    assert tags["cricket"] == pytest.approx(0.8)  # (1 - prior_weight) * cosine 1.0


def test_source_topics_act_as_a_prior() -> None:
    (vec,) = E.embed(["cricket test match wickets"])
    with_prior = tag_topics(vec, PROTOS, ["cricket", "markets"])
    assert with_prior["cricket"] == pytest.approx(1.0)
    assert "markets" not in with_prior  # a prior alone does not clear the bar
    assert tag_topics(vec, PROTOS, ["markets"], min_score=0.15)["markets"] == pytest.approx(
        0.2, abs=0.05
    )


def test_at_most_three_topics() -> None:
    (vec,) = E.embed(["same words"])
    protos = {f"t{i}": vec for i in range(6)}
    assert len(tag_topics(vec, protos, min_score=0.0)) == 3


def test_nothing_clears_the_threshold() -> None:
    (vec,) = E.embed(["completely unrelated gardening tips"])
    assert tag_topics(vec, PROTOS) == {}


@pytest.mark.integration
async def test_prototypes_are_stored_once_and_reloaded(db: AsyncSession) -> None:
    assert await ensure_prototypes(db, E) == len(CATALOGUE)
    assert await ensure_prototypes(db, E) == 0  # unchanged descriptions are not re-embedded
    stored = await load_prototypes(db)
    assert set(stored) == {t.slug for t in CATALOGUE}
    assert len(stored["ai"]) == 384
