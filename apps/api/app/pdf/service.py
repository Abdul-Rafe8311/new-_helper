"""Render an edition to PDF, keep it in storage and skip the work when nothing changed."""

import asyncio
import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models import Article, Depth, Edition, EditionItem, EditionStatus, Slot, Source, User
from app.models.user import ReaderProfile
from app.pdf.images import ImageCache
from app.pdf.layout import plan_pages
from app.pdf.render import render_pdf
from app.pdf.snapshot import EditionSnapshot, build_snapshot
from app.storage import Storage, StorageNotFoundError

log = structlog.get_logger(__name__)

PDF_CONTENT_TYPE = "application/pdf"

# The API runs in 512 MB: typeset one edition at a time per process.
_RENDER_GATE = asyncio.Lock()


class EditionNotReadyError(Exception):
    """Only a finished edition can be typeset."""


@dataclass(frozen=True)
class RenderResult:
    path: str
    paper_name: str
    rendered: bool  # False when the stored PDF was already current


def pdf_path(user_id: uuid.UUID, edition_date: date) -> str:
    return f"editions/{user_id}/{edition_date.isoformat()}.pdf"


def pdf_filename(paper_name: str, edition_date: date) -> str:
    """``{paper-name}-{date}.pdf`` with an ASCII-safe paper name."""
    ascii_name = unicodedata.normalize("NFKD", paper_name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-") or "newshelper"
    return f"{slug}-{edition_date.isoformat()}.pdf"


async def load_snapshot(
    session: AsyncSession, edition: Edition, settings: Settings
) -> EditionSnapshot:
    rows = (
        await session.execute(
            select(EditionItem, Article, Source.name)
            .join(Article, Article.id == EditionItem.article_id)
            .outerjoin(Source, Source.id == Article.source_id)
            .where(EditionItem.edition_id == edition.id)
            .order_by(EditionItem.position)
        )
    ).all()
    user = (await session.execute(select(User).where(User.id == edition.user_id))).scalar_one()
    profile = (
        await session.execute(select(ReaderProfile).where(ReaderProfile.user_id == user.id))
    ).scalar_one_or_none()
    items: list[dict[str, Any]] = []
    for item, article, source_name in rows:
        items.append(
            {
                "id": item.id,
                "section": item.section,
                "position": item.position,
                "slot": Slot(item.slot).value,
                "headline": item.headline,
                "summary": item.summary,
                "why_text": item.why_text,
                "score": item.score,
                "article": {
                    "url": article.url,
                    "title": article.title,
                    "headline": article.headline,
                    "summary": article.summary,
                    "excerpt": article.excerpt,
                    "key_facts": article.key_facts,
                    "source_name": source_name,
                    "author": article.author,
                    "image_url": article.image_url,
                    "published_at": article.published_at,
                    "topics": article.topics,
                },
            }
        )
    reader = {
        "display_name": user.display_name,
        "city": user.city,
        "paper_name": profile.paper_name if profile else None,
        "depth": Depth(profile.depth).value if profile else Depth.BALANCED.value,
        "topics": profile.topics if profile else {},
    }
    record = {
        "id": edition.id,
        "edition_date": edition.edition_date,
        "number": edition.number,
        "editor_note": edition.editor_note,
        "layout": edition.layout,
    }
    return build_snapshot(record, items, reader, page_size=settings.pdf_page_size)


async def render_edition(
    session: AsyncSession,
    storage: Storage,
    settings: Settings,
    edition: Edition,
    *,
    force: bool = False,
) -> RenderResult:
    """Make sure the edition's PDF is in storage and current; commits nothing itself."""
    if edition.status is not EditionStatus.READY:
        raise EditionNotReadyError(f"edition {edition.id} is {edition.status.value}")
    snapshot = await load_snapshot(session, edition, settings)
    path = pdf_path(edition.user_id, edition.edition_date)
    fingerprint = snapshot.fingerprint()
    if (
        not force
        and edition.pdf_hash == fingerprint
        and edition.pdf_path == path
        and await storage.exists(path)
    ):
        return RenderResult(path, snapshot.paper_name, rendered=False)

    wanted = {
        story_id: snapshot.story(story_id).image_url for story_id in plan_pages(snapshot).image_ids
    }
    cache = ImageCache(Path(settings.storage_local_dir) / "image-cache", settings.user_agent)
    try:
        images = await cache.fetch_many({k: u for k, u in wanted.items() if u})
    finally:
        await cache.aclose()
    pdf = await asyncio.to_thread(render_pdf, snapshot, images)  # CPU-bound, keep the loop free
    await storage.put(path, pdf, PDF_CONTENT_TYPE)
    edition.pdf_path = path
    edition.pdf_hash = fingerprint
    log.info("pdf_rendered", edition_id=str(edition.id), bytes=len(pdf), images=len(images))
    return RenderResult(path, snapshot.paper_name, rendered=True)


async def read_pdf(storage: Storage, path: str) -> bytes | None:
    try:
        return await storage.get(path)
    except StorageNotFoundError:
        return None
