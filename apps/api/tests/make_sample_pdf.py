"""Typeset the fixture edition into docs/samples/ for the README.

    cd apps/api && uv run python -m tests.make_sample_pdf

The fixture has no real photographs, so the lead and feature stories get generated stand-ins.
"""

import io
import random
from pathlib import Path

from PIL import Image, ImageDraw

from app.pdf.images import data_uri, shrink
from app.pdf.layout import plan_pages
from app.pdf.render import render_pdf
from tests.pdf_helpers import fixture_snapshot

OUT = Path(__file__).resolve().parents[3] / "docs" / "samples" / "newshelper-sample-edition.pdf"
PALETTES = [
    ((22, 38, 64), (196, 138, 74)),
    ((40, 54, 44), (214, 190, 120)),
    ((60, 30, 34), (226, 170, 140)),
]


def stand_in(seed: int) -> str:
    """A soft duotone landscape: sky gradient, a sun and layered hills."""
    rng = random.Random(seed)
    top, bottom = PALETTES[seed % len(PALETTES)]
    width, height = 1200, 800
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    for y in range(height):
        t = y / height
        draw.line(
            [(0, y), (width, y)],
            fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom, strict=True)),
        )
    sun_x, sun_y, radius = rng.randint(300, 900), rng.randint(180, 320), rng.randint(70, 110)
    draw.ellipse(
        [sun_x - radius, sun_y - radius, sun_x + radius, sun_y + radius], fill=(246, 232, 200)
    )
    for layer in range(4):
        base = 420 + layer * 90
        shade = tuple(int(c * (0.55 - layer * 0.1)) for c in top)
        points = [(0, height)]
        for x in range(0, width + 60, 60):
            points.append((x, base + rng.randint(-50, 50)))
        points.append((width, height))
        draw.polygon(points, fill=shade)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    jpeg = shrink(buffer.getvalue())
    assert jpeg is not None
    return data_uri(jpeg)


def main() -> None:
    snapshot = fixture_snapshot()
    plan = plan_pages(snapshot)
    # a front page with pictures, and one inside section with a picture to show the contrast
    inside = [b.stories[0] for b in plan.sections if b.stories and not b.explore]
    shown = [plan.front.lead, *plan.front.features, *inside[3:4]]
    images = {v.story.item_id: stand_in(i) for i, v in enumerate(shown)}
    pdf = render_pdf(snapshot, images)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(pdf)
    print(f"{OUT} ({len(pdf) // 1024} KB)")


if __name__ == "__main__":
    main()
