import io
import re
import subprocess
import sys
from pathlib import Path

import pytest
from pypdf import PdfReader

from app.pdf.images import data_uri, shrink
from app.pdf.layout import plan_pages
from app.pdf.render import fit_front_page, render_html, render_pdf
from app.pdf.snapshot import build_snapshot
from tests.pdf_helpers import fixture_records, fixture_snapshot

MAX_PDF_BYTES = 5 * 1024 * 1024
MAX_RENDER_SECONDS = 10


def words(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def squash(text: str) -> str:
    return re.sub(r"\s+", "", text)


def page_texts(pdf: bytes) -> list[str]:
    return [words(p.extract_text()) for p in PdfReader(io.BytesIO(pdf)).pages]


def link_targets(pdf: bytes) -> set[str]:
    found: set[str] = set()
    for page in PdfReader(io.BytesIO(pdf)).pages:
        for annotation in page.get("/Annots", []):
            action = annotation.get_object().get("/A")
            if action and "/URI" in action:
                found.add(str(action["/URI"]))
    return found


@pytest.fixture(scope="module")
def rendered() -> tuple[bytes, None]:
    return render_pdf(fixture_snapshot()), None


def test_renders_a_multi_page_pdf_that_is_small(rendered):
    pdf, _ = rendered
    assert pdf.startswith(b"%PDF")
    assert len(PdfReader(io.BytesIO(pdf)).pages) >= 2
    assert len(pdf) < MAX_PDF_BYTES


def test_a_cold_render_takes_under_ten_seconds():
    """Timed in a fresh interpreter: coverage tracing in this process slows the layout ~3x."""
    script = (
        "import time\n"
        "from tests.pdf_helpers import fixture_snapshot\n"
        "from app.pdf.render import render_pdf\n"
        "snapshot = fixture_snapshot()\n"
        "started = time.perf_counter()\n"
        "render_pdf(snapshot)\n"
        "print(time.perf_counter() - started)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    assert float(result.stdout.strip()) < MAX_RENDER_SECONDS


def test_masthead_and_every_headline_are_in_the_text(rendered):
    pdf, _ = rendered
    pages = page_texts(pdf)
    everything = " ".join(pages)
    assert "The Rafe Courier" in pages[0]
    assert "saturday, 17 october 2026" in pages[0].lower()
    squashed = squash(everything)
    for story in fixture_snapshot().stories:
        assert squash(story.headline) in squashed, story.headline  # a line may break at a hyphen


def test_every_headline_links_to_its_original_article(rendered):
    pdf, _ = rendered
    snapshot = fixture_snapshot()
    assert {s.url for s in snapshot.stories} <= link_targets(pdf)


def test_front_page_has_the_expected_furniture_on_one_sheet(rendered):
    pdf, _ = rendered
    first, second = page_texts(pdf)[:2]
    for part in ("Three things to know", "Editor's note", "IN BRIEF", "CURATED FOR RAFE"):
        assert part.lower() in first.lower()
    assert "Editor's note" not in second
    assert "Three things to know" not in second


def test_last_page_has_quiz_quote_and_colophon(rendered):
    pdf, _ = rendered
    last = page_texts(pdf)[-1]
    assert "The morning quiz" in last
    assert "quote of the day" in last.lower()
    assert "Curated for Rafe from 21 sources" in last
    assert "1-B, 2-B, 3-B" in last


def test_inside_pages_have_banners_and_the_explore_box(rendered):
    pdf, _ = rendered
    text = " ".join(page_texts(pdf)[1:-1])
    for banner in ("PAKISTAN", "TECHNOLOGY & AI", "SCIENCE", "OUTSIDE YOUR BUBBLE"):
        assert banner in text
    assert "Something far from your usual reading." in text


def test_letter_size_is_a_setting():
    a4 = PdfReader(io.BytesIO(render_pdf(fixture_snapshot()))).pages[0].mediabox
    letter = PdfReader(io.BytesIO(render_pdf(fixture_snapshot("Letter")))).pages[0].mediabox
    assert (round(a4.width), round(a4.height)) == (595, 842)
    assert (round(letter.width), round(letter.height)) == (612, 792)


def test_depth_changes_the_printed_paper():
    brief, deep = (
        " ".join(page_texts(render_pdf(fixture_snapshot(depth=d)))) for d in ("brief", "deep")
    )
    assert len(deep) > len(brief)
    fact = squash("Redshift of 14.4 confirmed by spectroscopy")  # an inside story's key fact
    assert fact in squash(deep)  # key-fact lists are for deep readers
    assert fact not in squash(brief)


def test_front_page_never_spills_even_with_long_copy():
    edition, items, reader = fixture_records(depth="deep")
    for item in items:
        item["summary"] = item["summary"] * 3
        item["headline"] = item["headline"] + " and the long consequences that follow from it"
    snapshot = build_snapshot(edition, items, reader)
    pdf = render_pdf(snapshot)
    assert "Editor's note" not in page_texts(pdf)[1]
    assert fit_front_page(snapshot).front.lead.summary  # still has a lead story


def test_text_is_escaped_and_missing_layout_parts_are_left_out():
    edition, items, reader = fixture_records()
    edition["layout"] = {}
    edition["editor_note"] = None
    items[0]["headline"] = "Fish & chips <script>alert(1)</script> at 5%"
    snapshot = build_snapshot(edition, items, reader)
    html = render_html(plan_pages(snapshot))
    assert "<script>" not in html
    assert "Fish &amp; chips &lt;script&gt;" in html
    text = " ".join(page_texts(render_pdf(snapshot)))
    assert squash("Fish & chips <script>alert(1)</script> at 5%") in squash(text)
    assert "Editor's note" not in text
    assert "The morning quiz" not in text


def test_story_images_are_embedded_and_missing_ones_are_skipped():
    from tests.test_pdf_images import png

    snapshot = fixture_snapshot()
    jpeg = shrink(png(900, 600))
    assert jpeg is not None
    with_image = render_pdf(snapshot, {snapshot.lead_item_id: data_uri(jpeg)})
    without = render_pdf(snapshot, {})
    # the lead story's QR code is always there; the picture is the second image
    assert len(PdfReader(io.BytesIO(without)).pages[0].images) == 1
    assert len(PdfReader(io.BytesIO(with_image)).pages[0].images) == 2
