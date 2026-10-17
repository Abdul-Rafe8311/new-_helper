"""Candidate summaries: one cheap-model call per 10 cluster representatives, once per article."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import LLMProvider
from app.ai.usage import BudgetGuard
from app.enrich.clusters import ARTICLE_TIME, representative
from app.models.content import Article, Source

log = structlog.get_logger(__name__)

WINDOW = timedelta(hours=24)
MAX_CANDIDATES = 250
BATCH_SIZE = 10
EXCERPT_CHARS = 1500
HEADLINE_WORDS = 12
EXTRACTIVE_MODEL = "extractive"

SYSTEM_PROMPT = f"""You are the wire editor of a morning newspaper. For each numbered article \
write: a neutral, factual headline of at most {HEADLINE_WORDS} words (no clickbait, no \
questions); a summary of exactly 2 sentences; exactly 3 short key facts; and the named \
entities (people, companies, teams, places) that appear in the article. Use only what the \
article says. Return one item per article, using its number as id."""


class Entities(BaseModel):
    people: list[str] = Field(default_factory=list)
    companies: list[str] = Field(default_factory=list)
    teams: list[str] = Field(default_factory=list)
    places: list[str] = Field(default_factory=list)


class ArticleDigest(BaseModel):
    id: int
    headline: str
    summary: str
    key_facts: list[str] = Field(min_length=3, max_length=3)
    entities: Entities = Field(default_factory=Entities)

    @field_validator("headline")
    @classmethod
    def _short_headline(cls, v: str) -> str:
        if len(v.split()) > HEADLINE_WORDS:
            raise ValueError(f"headline must be at most {HEADLINE_WORDS} words")
        return v.strip()


class DigestBatch(BaseModel):
    items: list[ArticleDigest]


@dataclass(frozen=True, slots=True)
class _Row:
    id: UUID
    cluster_id: int
    cluster_size: int
    quality: float
    length: int
    has_summary: bool


@dataclass(frozen=True, slots=True)
class Summarised:
    llm: int = 0
    extractive: int = 0
    llm_calls: int = 0


def first_sentences(text: str, n: int = 2) -> str:
    parts = re.split(r"(?<=[.!?])\s+", " ".join(text.split()))
    return " ".join(parts[:n]).strip()


async def select_candidates(
    session: AsyncSession, *, now: datetime | None = None, limit: int = MAX_CANDIDATES
) -> list[UUID]:
    """Representatives of recent clusters that have no summary yet, biggest stories first."""
    cutoff = (now or datetime.now(UTC)) - WINDOW
    length = func.coalesce(func.length(Article.content_text), func.length(Article.excerpt), 0)
    rows = [
        _Row(i, c, s or 1, q if q is not None else 0.5, ln, summ is not None)
        for i, c, s, q, ln, summ in (
            await session.execute(
                select(
                    Article.id,
                    Article.cluster_id,
                    Article.cluster_size,
                    Source.quality,
                    length,
                    Article.summary,
                )
                .outerjoin(Source, Source.id == Article.source_id)
                .where(Article.cluster_id.is_not(None), cutoff <= ARTICLE_TIME)
            )
        ).all()
    ]
    clusters: dict[int, list[_Row]] = {}
    for r in rows:
        clusters.setdefault(r.cluster_id, []).append(r)
    reps = [
        representative(members)
        for members in clusters.values()
        if not any(m.has_summary for m in members)  # never re-summarise a story
    ]
    reps.sort(key=lambda r: (r.cluster_size, r.quality), reverse=True)
    return [r.id for r in reps[:limit]]


def _prompt(batch: list[Article]) -> str:
    blocks = []
    for n, a in enumerate(batch, start=1):
        body = " ".join((a.content_text or a.excerpt or "").split())[:EXCERPT_CHARS]
        blocks.append(f"[{n}] {a.title}\n{body}")
    return "\n\n".join(blocks)


def _apply_extractive(article: Article) -> None:
    article.headline = article.title
    article.summary = first_sentences(article.content_text or article.excerpt or article.title)
    article.summary_model = EXTRACTIVE_MODEL


def _apply_digest(article: Article, digest: ArticleDigest, model: str) -> None:
    article.headline = digest.headline
    article.summary = digest.summary
    article.key_facts = digest.key_facts
    article.entities = digest.entities.model_dump()
    article.summary_model = model


async def summarise_candidates(
    session: AsyncSession,
    ids: list[UUID],
    llm: LLMProvider | None,
    guard: BudgetGuard | None,
    model: str,
) -> Summarised:
    """Summarise in batches of 10. Falls back to extractive text when the budget is spent,
    no LLM is configured, or the LLM fails for a batch."""
    articles = {
        a.id: a for a in (await session.scalars(select(Article).where(Article.id.in_(ids)))).all()
    }
    ordered = [articles[i] for i in ids if i in articles and articles[i].summary is None]
    done_llm = done_extractive = calls = 0
    for start in range(0, len(ordered), BATCH_SIZE):
        batch = ordered[start : start + BATCH_SIZE]
        digests: dict[int, ArticleDigest] = {}
        over_budget = guard is not None and await guard.exceeded()
        if llm is not None and not over_budget:
            try:
                calls += 1
                result = await llm.complete_json(
                    SYSTEM_PROMPT, _prompt(batch), DigestBatch, model, purpose="summaries"
                )
                digests = {d.id: d for d in result.items}
            except Exception:
                log.exception("summary_batch_failed", size=len(batch))
        elif over_budget:
            log.warning("llm_budget_exceeded", limit_usd=guard.limit_usd if guard else None)
        for n, article in enumerate(batch, start=1):
            if n in digests:
                _apply_digest(article, digests[n], model)
                done_llm += 1
            else:
                _apply_extractive(article)
                done_extractive += 1
        await session.commit()
    return Summarised(llm=done_llm, extractive=done_extractive, llm_calls=calls)
