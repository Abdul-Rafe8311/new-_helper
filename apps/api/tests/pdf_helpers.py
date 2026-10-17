"""Fixture edition for the PDF tests: JSON shaped like the Edition and EditionItem models."""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

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
