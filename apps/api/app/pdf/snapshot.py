"""Everything the PDF needs from an edition, detached from the database.

An ``EditionSnapshot`` is built from plain records shaped like the ``Edition`` and ``EditionItem``
models (plus each item's article and the reader's profile). The renderer, the content fingerprint
and the tests all work on this one object, so the fixture JSON in ``tests/fixtures`` and a live
edition go through the same code path.

``Edition.layout`` is the composer's JSON. The keys read here are ``lead_item_id``, ``sections``
(``[{"name", "item_ids"}]``), ``tagline``, ``three_things``, ``quote`` (``{"text", "source",
"item_id"}``), ``quiz`` (``[{"question", "options", "answer"}]``) and ``masthead`` (``paper_name``,
``city``, ``weather``). Every key is optional: a missing one is derived from the items or left out.
"""

import hashlib
import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# Bump when a template or the layout rules change, so stored PDFs are rendered again.
TEMPLATE_VERSION = 1

DEFAULT_PAPER_NAME = "The NewsHelper"
EXPLORE_SLOT = "explore"

PageSize = Literal["A4", "Letter"]
Slot = Literal["lead", "feature", "standard", "brief", "explore"]
Depth = Literal["brief", "balanced", "deep"]


class Story(BaseModel):
    item_id: str
    section: str
    position: int
    slot: Slot
    headline: str
    summary: str = ""
    key_facts: list[str] = Field(default_factory=list)
    why_text: str | None = None
    score: float = 0.0
    url: str
    source_name: str
    author: str | None = None
    image_url: str | None = None
    published_at: datetime | None = None
    topics: dict[str, float] = Field(default_factory=dict)


class Section(BaseModel):
    name: str
    item_ids: list[str]


class Quote(BaseModel):
    text: str
    source: str | None = None
    item_id: str | None = None


class QuizQuestion(BaseModel):
    question: str
    options: list[str]
    answer: int


class Weather(BaseModel):
    city: str | None = None
    condition: str | None = None
    temp_max_c: int | None = None


class EditionSnapshot(BaseModel):
    edition_id: str
    paper_name: str
    reader_name: str
    edition_date: date
    number: int
    city: str | None = None
    weather: Weather | None = None
    tagline: str | None = None
    editor_note: str | None = None
    depth: Depth = "balanced"
    page_size: PageSize = "A4"
    reader_topics: dict[str, float] = Field(default_factory=dict)
    lead_item_id: str
    sections: list[Section]
    three_things: list[str] = Field(default_factory=list)
    quote: Quote | None = None
    quiz: list[QuizQuestion] = Field(default_factory=list)
    stories: list[Story]

    def story(self, item_id: str) -> Story:
        return next(s for s in self.stories if s.item_id == item_id)

    @property
    def source_count(self) -> int:
        return len({s.source_name for s in self.stories})

    def fingerprint(self) -> str:
        """Hash of everything that changes the PDF; equal hashes mean the stored file is current."""
        payload = json.dumps(
            [TEMPLATE_VERSION, self.model_dump(mode="json")], sort_keys=True, ensure_ascii=False
        )
        return hashlib.sha256(payload.encode()).hexdigest()


def _clean(text: object) -> str:
    return " ".join(str(text or "").split())


def _facts(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    facts = []
    for entry in raw:
        value = entry.get("text") or entry.get("fact") if isinstance(entry, Mapping) else entry
        if _clean(value):
            facts.append(_clean(value))
    return facts


def _story(item: Mapping[str, Any]) -> Story:
    article: Mapping[str, Any] = item.get("article") or {}
    return Story(
        item_id=str(item["id"]),
        section=item["section"],
        position=item["position"],
        slot=item["slot"],
        headline=_clean(item.get("headline") or article.get("headline") or article.get("title")),
        summary=_clean(item.get("summary") or article.get("summary") or article.get("excerpt")),
        key_facts=_facts(article.get("key_facts")),
        why_text=_clean(item.get("why_text")) or None,
        score=float(item.get("score") or 0.0),
        url=article["url"],
        source_name=_clean(article.get("source_name")) or "Unknown source",
        author=_clean(article.get("author")) or None,
        image_url=article.get("image_url"),
        published_at=article.get("published_at"),
        topics=dict(article.get("topics") or {}),
    )


def _sections(layout: Mapping[str, Any], stories: Sequence[Story]) -> list[Section]:
    known = {s.item_id for s in stories}
    declared = [
        Section(name=s["name"], item_ids=[i for i in s.get("item_ids", []) if i in known])
        for s in layout.get("sections") or []
    ]
    placed = {i for s in declared for i in s.item_ids}
    leftovers: dict[str, list[Story]] = defaultdict(list)
    for story in stories:
        if story.item_id not in placed:
            leftovers[story.section].append(story)
    by_name = {s.name: s for s in declared}
    for name, members in leftovers.items():
        section = by_name.get(name) or Section(name=name, item_ids=[])
        if section.name not in by_name:
            declared.append(section)
        section.item_ids.extend(m.item_id for m in sorted(members, key=lambda m: m.position))
    return [s for s in declared if s.item_ids]


def build_snapshot(
    edition: Mapping[str, Any],
    items: Sequence[Mapping[str, Any]],
    reader: Mapping[str, Any],
    *,
    page_size: PageSize = "A4",
) -> EditionSnapshot:
    """``edition``/``items`` mirror the ``Edition``/``EditionItem`` columns; each item carries an
    ``article`` mapping (url, title, source_name, image_url, excerpt, key_facts, topics, ...) and
    ``reader`` holds ``display_name``, ``paper_name``, ``depth``, ``topics`` and ``city``."""
    layout: Mapping[str, Any] = edition.get("layout") or {}
    masthead: Mapping[str, Any] = layout.get("masthead") or {}
    stories = sorted((_story(i) for i in items), key=lambda s: s.position)
    if not stories:
        raise ValueError("an edition needs at least one story to be typeset")
    ids = {s.item_id for s in stories}
    lead = layout.get("lead_item_id")
    if lead not in ids:
        lead = next((s.item_id for s in stories if s.slot == "lead"), stories[0].item_id)
    quote = layout.get("quote")
    weather = masthead.get("weather")
    return EditionSnapshot(
        edition_id=str(edition["id"]),
        paper_name=_clean(masthead.get("paper_name") or reader.get("paper_name"))
        or DEFAULT_PAPER_NAME,
        reader_name=_clean(reader.get("display_name")) or "you",
        edition_date=edition["edition_date"],
        number=edition["number"],
        city=masthead.get("city") or reader.get("city"),
        weather=Weather(**weather) if weather else None,
        tagline=_clean(layout.get("tagline")) or None,
        editor_note=_clean(edition.get("editor_note")) or None,
        depth=reader.get("depth") or "balanced",
        page_size=page_size,
        reader_topics=dict(reader.get("topics") or {}),
        lead_item_id=lead,
        sections=_sections(layout, stories),
        three_things=[_clean(t) for t in layout.get("three_things") or [] if _clean(t)][:3],
        quote=Quote(**quote) if quote and quote.get("text") else None,
        quiz=[QuizQuestion(**q) for q in layout.get("quiz") or []],
        stories=stories,
    )
