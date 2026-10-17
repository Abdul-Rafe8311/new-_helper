import re
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import FakeLLM, LLMCall
from app.ai.usage import spend_today
from app.enrich.summaries import (
    EXTRACTIVE_MODEL,
    DigestBatch,
    first_sentences,
    select_candidates,
    summarise_candidates,
)
from app.models.ai import LLMUsage
from tests.factories import make_article, make_source

NOW = datetime(2026, 10, 17, 6, 0, tzinfo=UTC)
BODY = "First fact here. Second fact follows. Third sentence is dropped. Fourth too."


def responder(prompt: str, schema: type[BaseModel]) -> dict[str, Any]:
    ids = [int(n) for n in re.findall(r"^\[(\d+)\]", prompt, flags=re.M)]
    return {
        "items": [
            {
                "id": n,
                "headline": f"Neutral headline {n}",
                "summary": "One. Two.",
                "key_facts": ["a", "b", "c"],
                "entities": {"people": ["Ada"], "places": ["Lahore"]},
            }
            for n in ids
        ]
    }


class OverBudget:
    limit_usd = 1.0

    async def exceeded(self) -> bool:
        return True


def test_first_sentences() -> None:
    assert first_sentences(BODY) == "First fact here. Second fact follows."
    assert first_sentences("No punctuation") == "No punctuation"


async def make_story(db: AsyncSession, **fields: Any) -> Any:
    fields.setdefault("published_at", NOW - timedelta(hours=1))
    fields.setdefault("cluster_id", 1)
    fields.setdefault("cluster_size", 1)
    return await make_article(db, content_text=BODY, **fields)


@pytest.mark.integration
async def test_candidates_are_cluster_representatives_without_summaries(db: AsyncSession) -> None:
    good, poor = await make_source(db, quality=0.9), await make_source(db, quality=0.3)
    rep = await make_story(db, source_id=good.id, cluster_id=1, cluster_size=2)
    await make_story(db, source_id=poor.id, cluster_id=1, cluster_size=2)
    solo = await make_story(db, source_id=poor.id, cluster_id=2)
    await make_story(db, source_id=good.id, cluster_id=3, summary="done")  # already summarised
    await make_story(db, source_id=good.id, cluster_id=4, published_at=NOW - timedelta(hours=30))
    ids = await select_candidates(db, now=NOW)
    assert ids == [rep.id, solo.id]  # bigger story first; stale and summarised ones skipped
    assert await select_candidates(db, now=NOW, limit=1) == [rep.id]


@pytest.mark.integration
async def test_llm_summaries_are_stored_in_batches_of_ten(db: AsyncSession) -> None:
    arts = [await make_story(db, cluster_id=i) for i in range(1, 13)]
    llm = FakeLLM(responder=responder)
    stats = await summarise_candidates(db, [a.id for a in arts], llm, None, "claude-haiku-5-5")
    assert (stats.llm, stats.extractive, stats.llm_calls) == (12, 0, 2)
    assert [len(re.findall(r"^\[\d+\]", c["prompt"], flags=re.M)) for c in llm.calls] == [10, 2]
    assert llm.calls[0]["model"] == "claude-haiku-5-5"
    first = arts[0]
    await db.refresh(first)
    assert first.headline == "Neutral headline 1"
    assert first.key_facts == ["a", "b", "c"]
    assert first.entities["people"] == ["Ada"]
    assert first.summary_model == "claude-haiku-5-5"


@pytest.mark.integration
async def test_never_resummarises(db: AsyncSession) -> None:
    done = await make_story(db, summary="keep me", summary_model="x")
    llm = FakeLLM(responder=responder)
    stats = await summarise_candidates(db, [done.id], llm, None, "m")
    assert stats.llm_calls == 0
    await db.refresh(done)
    assert done.summary == "keep me"


@pytest.mark.integration
async def test_budget_guard_falls_back_to_extractive_summaries(db: AsyncSession) -> None:
    art = await make_story(db, title="Original title")
    llm = FakeLLM(responder=responder)
    stats = await summarise_candidates(db, [art.id], llm, OverBudget(), "m")  # type: ignore[arg-type]
    assert (stats.llm, stats.extractive, stats.llm_calls) == (0, 1, 0)
    assert llm.calls == []  # no LLM call once over budget
    await db.refresh(art)
    assert art.summary == "First fact here. Second fact follows."
    assert art.headline == "Original title"
    assert art.summary_model == EXTRACTIVE_MODEL


@pytest.mark.integration
async def test_failed_or_partial_llm_batch_falls_back_per_article(db: AsyncSession) -> None:
    a, b = await make_story(db, cluster_id=1), await make_story(db, cluster_id=2)
    only_first = FakeLLM([{"items": [responder("[1] x", DigestBatch)["items"][0]]}])
    stats = await summarise_candidates(db, [a.id, b.id], only_first, None, "m")
    assert (stats.llm, stats.extractive) == (1, 1)
    broken = FakeLLM([])  # raises: no scripted reply
    c = await make_story(db, cluster_id=3)
    stats = await summarise_candidates(db, [c.id], broken, None, "m")
    assert stats.extractive == 1


@pytest.mark.integration
async def test_spend_today_sums_only_today(db: AsyncSession) -> None:
    now = datetime.now(UTC)
    calls = [LLMCall(model="claude-haiku-5-5", purpose="p", output_tokens=1_000_000)] * 2
    for c in calls:
        db.add(
            LLMUsage(model=c.model, purpose=c.purpose, output_tokens=1_000_000, cost_usd=c.cost_usd)
        )
    db.add(LLMUsage(model="m", purpose="p", cost_usd=99.0, created_at=now - timedelta(days=2)))
    await db.flush()
    assert await spend_today(db) == pytest.approx(1.0)
