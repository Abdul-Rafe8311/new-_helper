"""Fixture edition for the PDF tests: JSON shaped like the Edition and EditionItem models."""

import json
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Article, Edition, EditionItem, EditionStatus, Slot, Source, SourceKind, User
from app.pdf.snapshot import EditionSnapshot, PageSize, build_snapshot

FIXTURE = Path(__file__).parent / "fixtures" / "edition_layout.json"


def fixture_records(**reader: Any) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    edition = raw["edition"]
    edition["edition_date"] = date.fromisoformat(edition["edition_date"])
    for item in raw["items"]:
        item["article"]["published_at"] = datetime.fromisoformat(item["article"]["published_at"])
    return edition, raw["items"], {**raw["reader"], **reader}


def fixture_snapshot(page_size: PageSize = "A4", **reader: Any) -> EditionSnapshot:
    edition, items, profile = fixture_records(**reader)
    return build_snapshot(edition, items, profile, page_size=page_size)


async def make_fixture_edition(
    session: AsyncSession, user: User, *, status: EditionStatus = EditionStatus.READY
) -> Edition:
    """Store the fixture edition for ``user`` (fresh ids each call): sources, articles, items."""
    record, items, _ = fixture_records()
    fresh = {old: str(uuid.uuid4()) for old in [record["id"], *(i["id"] for i in items)]}
    layout_json = json.dumps(record["layout"])
    for old, new in fresh.items():
        layout_json = layout_json.replace(old, new)
    edition = Edition(
        id=uuid.UUID(fresh[record["id"]]),
        user_id=user.id,
        edition_date=record["edition_date"],
        number=record["number"],
        status=status,
        title=record["title"],
        editor_note=record["editor_note"],
        layout=json.loads(layout_json),
    )
    sources = {
        name: Source(
            name=name, kind=SourceKind.RSS, url=f"https://feeds.example.com/{uuid.uuid4()}"
        )
        for name in dict.fromkeys(i["article"]["source_name"] for i in items)
    }
    session.add_all([edition, *sources.values()])
    await session.flush()  # two flushes in all: this one for the parents, one for the children
    for n, raw in enumerate(items):
        meta = raw["article"]
        article = Article(
            id=uuid.uuid4(),
            source_id=sources[meta["source_name"]].id,
            url=f"{meta['url']}?u={uuid.uuid4()}",
            title=meta["title"],
            author=meta["author"],
            excerpt=meta["excerpt"],
            key_facts=meta["key_facts"],
            topics=meta["topics"],
            published_at=meta["published_at"],
        )
        item = EditionItem(
            id=uuid.UUID(fresh[raw["id"]]),
            edition_id=edition.id,
            article_id=article.id,
            section=raw["section"],
            position=n,
            slot=Slot(raw["slot"]),
            headline=raw["headline"],
            summary=raw["summary"],
            why_text=raw["why_text"],
            score=raw["score"],
        )
        session.add_all([article, item])
    await session.flush()
    return edition
