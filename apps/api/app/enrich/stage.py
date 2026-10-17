"""The `enrich` pipeline stage: embed -> tag topics -> cluster -> summarise candidates."""

import asyncio
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.embedder import Embedder, FastEmbedEmbedder, article_embedding_text
from app.ai.factory import build_llm
from app.ai.llm import LLMProvider
from app.ai.usage import BudgetGuard
from app.core.config import Settings
from app.db.session import get_sessionmaker
from app.enrich.clusters import cluster_recent
from app.enrich.summaries import select_candidates, summarise_candidates
from app.enrich.topics import ensure_prototypes, load_prototypes, tag_topics
from app.models.content import Article, Source
from app.models.edition import PipelineRun
from app.models.enums import RunStatus

log = structlog.get_logger(__name__)

EMBED_CHUNK = 256


@dataclass
class EnrichReport:
    prototypes_embedded: int = 0
    embedded: int = 0
    tagged: int = 0
    articles_clustered: int = 0
    clusters: int = 0
    multi_article_clusters: int = 0
    candidates: int = 0
    summaries_llm: int = 0
    summaries_extractive: int = 0
    llm_calls: int = 0
    llm_cost_usd: float = 0.0


async def embed_and_tag(session: AsyncSession, embedder: Embedder, report: EnrichReport) -> None:
    """Embed articles that have no vector yet and tag their topics."""
    report.prototypes_embedded = await ensure_prototypes(session, embedder)
    prototypes = await load_prototypes(session)
    while True:
        rows = (
            await session.execute(
                select(Article, Source.topics)
                .outerjoin(Source, Source.id == Article.source_id)
                .where(Article.embedding.is_(None))
                .order_by(Article.created_at)
                .limit(EMBED_CHUNK)
            )
        ).all()
        if not rows:
            return
        texts = [article_embedding_text(a.title, a.excerpt, a.content_text) for a, _ in rows]
        vectors = await asyncio.to_thread(embedder.embed, texts)  # CPU-bound, keep the loop free
        for (article, source_topics), vector in zip(rows, vectors, strict=True):
            article.embedding = vector
            article.topics = tag_topics(vector, prototypes, source_topics or [])
            report.embedded += 1
            report.tagged += bool(article.topics)
        await session.commit()


async def run_enrich(
    sessionmaker: async_sessionmaker[AsyncSession],
    embedder: Embedder,
    llm: LLMProvider | None,
    guard: BudgetGuard,
    model: str,
    *,
    now: datetime | None = None,
) -> EnrichReport:
    report = EnrichReport()
    spent_before = await guard.spent()
    async with sessionmaker() as session:
        await embed_and_tag(session, embedder, report)
        counts = await cluster_recent(session, now=now)
        report.articles_clustered = counts["articles"]
        report.clusters = counts["clusters"]
        report.multi_article_clusters = counts["multi_article_clusters"]
        candidates = await select_candidates(session, now=now)
        report.candidates = len(candidates)
        summarised = await summarise_candidates(session, candidates, llm, guard, model)
        report.summaries_llm = summarised.llm
        report.summaries_extractive = summarised.extractive
        report.llm_calls = summarised.llm_calls
    report.llm_cost_usd = round(await guard.spent() - spent_before, 6)
    return report


async def enrich(settings: Settings) -> None:
    sessionmaker = get_sessionmaker()
    guard = BudgetGuard(sessionmaker, settings.llm_daily_budget_usd)
    embedder = FastEmbedEmbedder(
        settings.embedding_model, settings.embedding_dim, settings.fastembed_cache_dir
    )
    started = datetime.now(UTC)
    report = EnrichReport()
    status = RunStatus.FAILED
    try:
        report = await run_enrich(
            sessionmaker,
            embedder,
            build_llm(settings, sessionmaker),
            guard,
            settings.llm_fast_model,
        )
        status = RunStatus.SUCCEEDED
    finally:
        async with sessionmaker() as session:
            session.add(
                PipelineRun(
                    stage="enrich",
                    started_at=started,
                    finished_at=datetime.now(UTC),
                    status=status,
                    stats=asdict(report),
                )
            )
            await session.commit()
    log.info("enrich_done", **asdict(report), budget_usd=settings.llm_daily_budget_usd)
