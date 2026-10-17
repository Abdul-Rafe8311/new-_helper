"""Typeset an edition snapshot into PDF bytes with WeasyPrint."""

from collections.abc import Mapping
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import CSS, HTML, Document
from weasyprint.text.fonts import FontConfiguration

from app.pdf.layout import MAX_SQUEEZE, PagePlan, plan_pages
from app.pdf.qr import qr_data_uri
from app.pdf.snapshot import EditionSnapshot

PDF_DIR = Path(__file__).parent
TEMPLATE_DIR = PDF_DIR / "templates"
STATIC_DIR = PDF_DIR / "static"

_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _css_string(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def page_css(snapshot: EditionSnapshot) -> str:
    """The parts of the stylesheet that depend on the edition: page size and running header."""
    header = f"{snapshot.paper_name} · {snapshot.edition_date.strftime('%A %d %B %Y')}"
    return (
        f"@page {{ size: {snapshot.page_size}; "
        f'@top-center {{ content: "{_css_string(header)}"; }} }}'
    )


def render_html(
    plan: PagePlan, images: Mapping[str, str] | None = None, *, front_only: bool = False
) -> str:
    return _env.get_template("edition.html").render(
        snap=plan.snapshot,
        plan=plan,
        images=images or {},
        qr=qr_data_uri(plan.front.lead.url),
        front_only=front_only,
    )


# Registering the bundled fonts and parsing the stylesheet is a large part of a render, and a render
# runs several times per edition (front-page fitting), so both are done once per process.
_fonts = FontConfiguration()
_stylesheet: CSS | None = None


def _stylesheets(snapshot: EditionSnapshot) -> list[CSS]:
    global _stylesheet
    if _stylesheet is None:
        _stylesheet = CSS(filename=str(STATIC_DIR / "newspaper.css"), font_config=_fonts)
    return [_stylesheet, CSS(string=page_css(snapshot), font_config=_fonts)]


def _document(html: str, snapshot: EditionSnapshot) -> Document:
    return HTML(string=html, base_url=str(STATIC_DIR) + "/").render(
        stylesheets=_stylesheets(snapshot), font_config=_fonts
    )


def fit_front_page(snapshot: EditionSnapshot, images: Mapping[str, str] | None = None) -> PagePlan:
    """The fullest plan whose front page still fits on one sheet (it never spills onto page 2)."""
    for squeeze in range(MAX_SQUEEZE + 1):
        plan = plan_pages(snapshot, squeeze)
        if len(_document(render_html(plan, images, front_only=True), snapshot).pages) == 1:
            break
    return plan


def render_pdf(snapshot: EditionSnapshot, images: Mapping[str, str] | None = None) -> bytes:
    """Typeset the edition; ``images`` maps item ids to data URIs for stories with a picture."""
    plan = fit_front_page(snapshot, images)
    pdf: bytes = _document(render_html(plan, images), snapshot).write_pdf()
    return pdf
