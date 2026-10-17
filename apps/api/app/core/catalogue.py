"""The topic catalogue the interests page browses: every onboarding topic plus more.

Onboarding and the nightly tagger keep using the 35 topics in `taxonomy.TOPICS`; the catalogue
adds to them and never renames a key, so existing profiles keep their weights.
"""

from dataclasses import dataclass
from enum import StrEnum

from app.core.taxonomy import TOPICS, Topic
from app.onboarding.profile_builder import EXPLICIT_WEIGHT

# Where a topic starts when a reader adds it by hand: what onboarding gives a topic they picked.
DEFAULT_ADD_WEIGHT = EXPLICIT_WEIGHT


class Section(StrEnum):
    TECHNOLOGY = "Technology"
    SCIENCE = "Science"
    WORLD = "World"
    PAKISTAN = "Pakistan"
    BUSINESS = "Business and Markets"
    SPORT = "Sport"
    CULTURE = "Culture"
    HEALTH = "Health"
    CLIMATE = "Climate"
    ENTERTAINMENT = "Entertainment"


@dataclass(frozen=True, slots=True)
class CatalogueTopic:
    slug: str
    label: str
    section: Section
    description: str


_TE, _SC, _WO, _PK, _BU, _SP, _CU, _HE, _CL, _EN = tuple(Section)

# onboarding topic -> section
_SECTION_OF: dict[str, Section] = {
    **dict.fromkeys(("tech", "ai", "software", "cybersecurity", "gadgets"), _TE),
    **dict.fromkeys(("science", "space"), _SC),
    **dict.fromkeys(("world", "south-asia", "middle-east", "us-politics", "europe"), _WO),
    "pakistan": _PK,
    **dict.fromkeys(
        ("business", "markets", "economy", "startups", "crypto", "personal-finance", "careers"), _BU
    ),
    **dict.fromkeys(("cricket", "football", "f1", "sports"), _SP),
    **dict.fromkeys(("books", "design", "food", "travel", "education"), _CU),
    "health": _HE,
    **dict.fromkeys(("climate", "energy"), _CL),
    **dict.fromkeys(("film-tv", "music", "gaming"), _EN),
}

_EXTRA: tuple[CatalogueTopic, ...] = (
    CatalogueTopic(
        "semiconductors",
        "Chips & Hardware",
        _TE,
        "Semiconductors, chipmakers and computing hardware.",
    ),
    CatalogueTopic(
        "robotics", "Robotics", _TE, "Robots, automation, drones and autonomous machines."
    ),
    CatalogueTopic(
        "social-media",
        "Social Media",
        _TE,
        "Social networks, creators, platforms and online culture.",
    ),
    CatalogueTopic(
        "physics", "Physics", _SC, "Particles, quantum physics, materials and cosmology."
    ),
    CatalogueTopic(
        "biology", "Biology & Genetics", _SC, "Genes, evolution, cells, animals and ecosystems."
    ),
    CatalogueTopic(
        "archaeology", "Archaeology", _SC, "Excavations, ancient civilisations and human origins."
    ),
    CatalogueTopic(
        "china", "China & Asia-Pacific", _WO, "China, Japan, Korea, ASEAN and the Pacific."
    ),
    CatalogueTopic("africa", "Africa", _WO, "Politics, economies and societies across Africa."),
    CatalogueTopic(
        "latin-america", "Latin America", _WO, "News from Brazil, Mexico, Argentina and the region."
    ),
    CatalogueTopic(
        "russia-ukraine", "Russia & Ukraine", _WO, "The war in Ukraine, Russia and its neighbours."
    ),
    CatalogueTopic(
        "pakistan-politics",
        "Pakistan Politics",
        _PK,
        "Parliament, parties, courts and the military in Pakistan.",
    ),
    CatalogueTopic(
        "pakistan-economy",
        "Pakistan Economy",
        _PK,
        "The rupee, the IMF, budgets, the stock exchange and trade in Pakistan.",
    ),
    CatalogueTopic(
        "real-estate", "Real Estate", _BU, "Property markets, housing, construction and mortgages."
    ),
    CatalogueTopic(
        "fintech", "Banking & Fintech", _BU, "Banks, payments, digital finance and lending."
    ),
    CatalogueTopic(
        "tennis", "Tennis", _SP, "Grand Slams, the ATP and WTA tours and their players."
    ),
    CatalogueTopic(
        "basketball", "Basketball", _SP, "The NBA, EuroLeague and international basketball."
    ),
    CatalogueTopic("olympics", "Olympics", _SP, "The Olympic and Paralympic Games and athletics."),
    CatalogueTopic("art", "Art", _CU, "Museums, galleries, artists and exhibitions."),
    CatalogueTopic("fashion", "Fashion", _CU, "Clothing, designers, runways and style."),
    CatalogueTopic(
        "mental-health",
        "Mental Health",
        _HE,
        "Psychology, stress, therapy and emotional wellbeing.",
    ),
    CatalogueTopic("fitness", "Fitness", _HE, "Exercise, sleep, training and staying active."),
    CatalogueTopic(
        "renewables", "Renewables", _CL, "Solar, wind, batteries and clean energy projects."
    ),
    CatalogueTopic(
        "wildlife", "Wildlife & Nature", _CL, "Animals, habitats, oceans and biodiversity."
    ),
    CatalogueTopic(
        "streaming", "Streaming", _EN, "Streaming services, new series and what to watch."
    ),
    CatalogueTopic(
        "celebrity-news",
        "Celebrity News",
        _EN,
        "Stars, awards, red carpets and entertainment gossip.",
    ),
)


def _from_onboarding(t: Topic) -> CatalogueTopic:
    return CatalogueTopic(t.slug, t.label, _SECTION_OF[t.slug], t.description)


CATALOGUE: tuple[CatalogueTopic, ...] = (*map(_from_onboarding, TOPICS), *_EXTRA)
CATALOGUE_BY_SLUG: dict[str, CatalogueTopic] = {t.slug: t for t in CATALOGUE}
CATALOGUE_SLUGS: frozenset[str] = frozenset(CATALOGUE_BY_SLUG)

__all__ = ["CATALOGUE", "CATALOGUE_BY_SLUG", "CATALOGUE_SLUGS", "DEFAULT_ADD_WEIGHT", "Section"]
