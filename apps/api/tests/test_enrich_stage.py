import re
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.embedder import FakeEmbedder
from app.ai.llm import FakeLLM
from app.ai.usage import BudgetGuard, DBUsageRecorder
from app.enrich.stage import run_enrich
from app.pipeline import STAGE_FNS
from tests.factories import make_article, make_source

NOW = datetime(2026, 10, 17, 6, 0, tzinfo=UTC)
BANK = "central bank raises interest rates as inflation worries markets"


def responder(prompt: str, schema: type[BaseModel]) -> dict[str, Any]:
    ids = [int(n) for n in re.findall(r"^\[(\d+)\]", prompt, flags=re.M)]
    return {
        "items": [
            {"id": n, "headline": "Rates rise", "summary": "A. B.", "key_facts": ["1", "2", "3"]}
            for n in ids
        ]
    }


def test_enrich_is_registered_as_a_pipeline_stage() -> None:
    assert "enrich" in STAGE_FNS


@pytest.mark.integration
async def test_ingest_then_enrich_gives_embeddings_topics_clusters_and_summaries(
    db: AsyncSession,
) -> None:
    sessionmaker = async_sessionmaker(
        bind=db.bind, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    src = await make_source(db, topics=["markets"], quality=0.8)
    published = NOW - timedelta(hours=2)
    a = await make_article(
        db, source_id=src.id, title=BANK, content_text=BANK, published_at=published
    )
    b = await make_article(
        db, source_id=src.id, title=BANK + " again", content_text=BANK, published_at=published
    )
    c = await make_article(
        db,
        source_id=src.id,
        title="cricket final",
        content_text="cricket final wickets",
        published_at=published,
    )
    await db.commit()

    guard = BudgetGuard(sessionmaker, limit_usd=5.0)
    llm = FakeLLM(responder=responder, cost_per_call=0.25, recorder=DBUsageRecorder(sessionmaker))
    report = await run_enrich(sessionmaker, FakeEmbedder(), llm, guard, "claude-haiku-5-5", now=NOW)

    for art in (a, b, c):
        await db.refresh(art)
        assert art.embedding is not None
        assert art.cluster_id is not None
    assert a.cluster_id == b.cluster_id != c.cluster_id
    assert a.cluster_size == 2
    assert report.embedded == 3
    assert report.clusters == 2
    assert report.candidates == 2  # one representative per story
    assert report.summaries_llm == 2
    assert report.llm_calls == 1
    assert report.llm_cost_usd == pytest.approx(0.25, abs=1e-4)
    assert sum(x.summary is not None for x in (a, b, c)) == 2

    # a second run does no new work: nothing to embed, nothing left to summarise
    again = await run_enrich(sessionmaker, FakeEmbedder(), llm, guard, "claude-haiku-5-5", now=NOW)
    assert (again.embedded, again.candidates, again.llm_calls) == (0, 0, 0)
