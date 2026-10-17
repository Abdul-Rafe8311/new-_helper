"""Turns an edition snapshot into the page plan the templates print.

The reader's profile shapes the presentation as well as the content:

* depth ``brief``: shorter summaries, one full story per section and the rest as briefs, a longer
  briefs column; ``deep``: whole summaries and key-fact lists, a shorter briefs column;
* inside sections follow the reader's topic weights (the explore section always closes the paper);
* the lead story is the composer's choice.
"""

import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from app.pdf.snapshot import Depth, EditionSnapshot, Story

EXPLORE_SECTION_SLOT = "explore"
_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"\u201c\u2018(])")

# per depth: summary character budgets (lead, feature, standard, brief), key facts shown on
# features/standard stories, front-page features and briefs.
_BUDGET: dict[Depth, tuple[int, int, int, int]] = {
    "brief": (420, 200, 0, 130),
    "balanced": (560, 380, 330, 150),
    "deep": (1400, 760, 620, 220),
}
_FACTS: dict[Depth, int] = {"brief": 0, "balanced": 0, "deep": 4}
_FRONT_FEATURES: dict[Depth, int] = {"brief": 2, "balanced": 3, "deep": 3}
_FRONT_BRIEFS: dict[Depth, int] = {"brief": 8, "balanced": 6, "deep": 4}
BIG_SECTION_STORIES = 4


def shorten(text: str, limit: int) -> str:
    """Whole sentences up to ``limit`` characters (the first sentence is always kept)."""
    if limit <= 0 or len(text) <= limit:
        return text
    kept: list[str] = []
    for sentence in _SENTENCE.split(text):
        if kept and len(" ".join([*kept, sentence])) > limit:
            break
        kept.append(sentence)
    result = " ".join(kept)
    if len(result) > limit * 1.4:  # one huge sentence: cut at a word
        result = result[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return result


def domain_of(url: str) -> str:
    host = urlsplit(url).hostname or ""
    return host.removeprefix("www.")


@dataclass(frozen=True)
class StoryView:
    story: Story
    summary: str
    facts: list[str]
    image: str | None = None  # data URI, filled in once images are fetched

    @property
    def headline(self) -> str:
        return self.story.headline

    @property
    def url(self) -> str:
        return self.story.url

    @property
    def source(self) -> str:
        return self.story.source_name

    @property
    def domain(self) -> str:
        return domain_of(self.story.url)

    @property
    def byline(self) -> str:
        parts = [self.story.author] if self.story.author else []
        return " · ".join([*parts, self.story.source_name])


@dataclass(frozen=True)
class SectionBlock:
    name: str
    explore: bool
    stories: list[StoryView]
    briefs: list[StoryView]
    pull_quote: str | None
    big: bool


@dataclass(frozen=True)
class FrontPage:
    lead: StoryView
    features: list[StoryView]
    briefs: list[StoryView]


@dataclass(frozen=True)
class PagePlan:
    snapshot: EditionSnapshot
    front: FrontPage
    sections: list[SectionBlock]
    date_line: str = ""
    image_ids: list[str] = field(default_factory=list)


_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]  # fmt: skip


def date_line(snapshot: EditionSnapshot) -> str:
    d = snapshot.edition_date
    parts = [
        f"{_WEEKDAYS[d.weekday()]}, {d.day} {_MONTHS[d.month - 1]} {d.year}",
        f"No. {snapshot.number}",
    ]
    place = snapshot.city or (snapshot.weather.city if snapshot.weather else None)
    weather = snapshot.weather
    if place and weather and weather.temp_max_c is not None:
        condition = f", {weather.condition.lower()}" if weather.condition else ""
        parts.append(f"{place} {weather.temp_max_c}°C{condition}")
    elif place:
        parts.append(place)
    return " · ".join(parts)


def affinity(story: Story, weights: dict[str, float]) -> float:
    return sum(weights.get(topic, 0.0) * w for topic, w in story.topics.items())


def order_sections(snapshot: EditionSnapshot, names: list[str]) -> list[str]:
    """Sections the reader cares about most come first; ties keep the composer's order."""
    by_name = {s.name: s for s in snapshot.sections}

    def weight(name: str) -> float:
        stories = sorted(
            (affinity(snapshot.story(i), snapshot.reader_topics) for i in by_name[name].item_ids),
            reverse=True,
        )[:3]
        return sum(stories) / len(stories) if stories else 0.0

    explore = [
        n
        for n in names
        if all(snapshot.story(i).slot == EXPLORE_SECTION_SLOT for i in by_name[n].item_ids)
    ]
    rest = [n for n in names if n not in explore]
    rest.sort(key=lambda n: (-weight(n), names.index(n)))
    return [*rest, *explore]


def _view(story: Story, kind: int, depth: Depth) -> StoryView:
    limit = _BUDGET[depth][kind]
    facts = story.key_facts[: _FACTS[depth]] if kind in (0, 1, 2) else []
    return StoryView(story=story, summary=shorten(story.summary, limit), facts=facts)


def _pull_quote(stories: list[StoryView]) -> str | None:
    for view in stories:
        sentences = _SENTENCE.split(view.story.summary)
        if len(sentences) >= 3 and 40 <= len(sentences[1]) <= 150:
            return sentences[1]
    return None


def plan_pages(snapshot: EditionSnapshot) -> PagePlan:
    depth = snapshot.depth
    lead_story = snapshot.story(snapshot.lead_item_id)
    others = [s for s in snapshot.stories if s.item_id != lead_story.item_id]

    # Front page: best feature per section first, so the page is not three stories on one topic.
    features: list[Story] = []
    pool = sorted((s for s in others if s.slot == "feature"), key=lambda s: -s.score)
    for story in pool:
        if len(features) < _FRONT_FEATURES[depth] and all(
            story.section != f.section for f in features
        ):
            features.append(story)
    for story in pool:
        if len(features) < _FRONT_FEATURES[depth] and story not in features:
            features.append(story)
    front_briefs = sorted((s for s in others if s.slot == "brief"), key=lambda s: -s.score)[
        : _FRONT_BRIEFS[depth]
    ]
    on_front = {
        lead_story.item_id,
        *(s.item_id for s in features),
        *(s.item_id for s in front_briefs),
    }

    names = order_sections(snapshot, [s.name for s in snapshot.sections])
    by_name = {s.name: s for s in snapshot.sections}
    blocks: list[SectionBlock] = []
    for name in names:
        members = [snapshot.story(i) for i in by_name[name].item_ids if i not in on_front]
        if not members:
            continue
        explore = all(m.slot == EXPLORE_SECTION_SLOT for m in members)
        full = [m for m in members if m.slot != "brief"]
        briefs = [m for m in members if m.slot == "brief"]
        if depth == "brief" and not explore and len(full) > 1:
            briefs = [*full[1:], *briefs]  # one real story per section, the rest as briefs
            full = full[:1]
        views = [
            _view(m, 1 if m.slot == "feature" else 2 if depth != "brief" else 1, depth)
            for m in full
        ]
        blocks.append(
            SectionBlock(
                name=name,
                explore=explore,
                stories=views,
                briefs=[_view(b, 3, depth) for b in briefs],
                pull_quote=None if explore else _pull_quote(views),
                big=len(members) >= BIG_SECTION_STORIES,
            )
        )

    front = FrontPage(
        lead=_view(lead_story, 0, depth),
        features=[_view(f, 1, depth) for f in features],
        briefs=[_view(b, 3, depth) for b in front_briefs],
    )
    shown = [front.lead, *front.features, *(s for b in blocks for s in b.stories[:1])]
    return PagePlan(
        snapshot=snapshot,
        front=front,
        sections=blocks,
        date_line=date_line(snapshot),
        image_ids=[v.story.item_id for v in shown if v.story.image_url],
    )
