"""Fixed topic taxonomy.

Descriptions are written to be embedded: later stages tag articles by cosine
similarity between an article embedding and each topic's description embedding.
"""

from dataclasses import dataclass
from enum import StrEnum


class TopicGroup(StrEnum):
    NEWS = "News"
    MONEY = "Money"
    TECH = "Tech"
    SCIENCE = "Science"
    LIFE = "Life"
    SPORT = "Sport"
    CULTURE = "Culture"


@dataclass(frozen=True, slots=True)
class Topic:
    slug: str
    label: str
    group: TopicGroup
    description: str


_N, _M, _T, _S, _L, _SP, _C = (
    TopicGroup.NEWS,
    TopicGroup.MONEY,
    TopicGroup.TECH,
    TopicGroup.SCIENCE,
    TopicGroup.LIFE,
    TopicGroup.SPORT,
    TopicGroup.CULTURE,
)

TOPICS: tuple[Topic, ...] = (
    Topic("world", "World", _N, "International news, diplomacy, conflicts and global affairs."),
    Topic(
        "pakistan", "Pakistan", _N, "News about Pakistan's politics, society, cities and people."
    ),
    Topic(
        "south-asia",
        "South Asia",
        _N,
        "Regional news from India, Afghanistan, Bangladesh and Sri Lanka.",
    ),
    Topic(
        "middle-east",
        "Middle East",
        _N,
        "Politics, conflict and society across the Middle East and Gulf.",
    ),
    Topic(
        "us-politics",
        "US Politics",
        _N,
        "American government, elections, Congress, courts and the White House.",
    ),
    Topic("europe", "Europe", _N, "Politics and news from the UK, the EU and wider Europe."),
    Topic(
        "business",
        "Business",
        _M,
        "Companies, corporate strategy, earnings, deals and industry news.",
    ),
    Topic("markets", "Markets", _M, "Stock markets, bonds, currencies, commodities and investing."),
    Topic("economy", "Economy", _M, "Inflation, interest rates, jobs, trade and economic policy."),
    Topic(
        "startups", "Startups", _M, "Founders, venture capital, funding rounds and new companies."
    ),
    Topic("crypto", "Crypto", _M, "Bitcoin, blockchains, digital assets and their regulation."),
    Topic(
        "personal-finance",
        "Personal Finance",
        _M,
        "Saving, budgeting, taxes, property and managing money.",
    ),
    Topic("tech", "Technology", _T, "Big tech companies, consumer technology and the internet."),
    Topic(
        "ai",
        "Artificial Intelligence",
        _T,
        "Machine learning, large language models, AI research and AI policy.",
    ),
    Topic(
        "software",
        "Software & Dev",
        _T,
        "Programming, open source, developer tools and software engineering.",
    ),
    Topic(
        "cybersecurity", "Cybersecurity", _T, "Hacking, data breaches, privacy and online security."
    ),
    Topic("gadgets", "Gadgets", _T, "Phones, laptops, wearables and consumer device reviews."),
    Topic(
        "science", "Science", _S, "Research discoveries in physics, biology, chemistry and beyond."
    ),
    Topic("space", "Space", _S, "Astronomy, space exploration, rockets and missions."),
    Topic("health", "Health", _S, "Medicine, public health, disease, nutrition and wellbeing."),
    Topic(
        "climate",
        "Climate & Environment",
        _S,
        "Climate change, weather extremes, nature and conservation.",
    ),
    Topic("energy", "Energy", _S, "Oil, gas, renewables, electricity and the energy transition."),
    Topic("food", "Food", _L, "Cooking, recipes, restaurants and food culture."),
    Topic("travel", "Travel", _L, "Destinations, tourism, airlines and travel tips."),
    Topic("education", "Education", _L, "Schools, universities, learning and education policy."),
    Topic("careers", "Work & Careers", _L, "Jobs, the workplace, productivity and career advice."),
    Topic(
        "cricket",
        "Cricket",
        _SP,
        "Test, ODI and T20 cricket, the PSL, IPL and international series.",
    ),
    Topic(
        "football",
        "Football",
        _SP,
        "Soccer leagues, the Premier League, Champions League and World Cup.",
    ),
    Topic("f1", "Formula 1", _SP, "Formula One races, drivers, teams and motorsport."),
    Topic(
        "sports", "Other Sport", _SP, "Tennis, basketball, the Olympics and other sporting events."
    ),
    Topic(
        "film-tv",
        "Film & TV",
        _C,
        "Movies, television series, streaming and entertainment industry.",
    ),
    Topic("music", "Music", _C, "Artists, albums, concerts and the music industry."),
    Topic("books", "Books", _C, "New books, authors, literature and reading."),
    Topic(
        "design",
        "Design & Architecture",
        _C,
        "Graphic design, product design, architecture and interiors.",
    ),
    Topic("gaming", "Gaming", _C, "Video games, consoles, game studios and esports."),
)

TOPICS_BY_SLUG: dict[str, Topic] = {t.slug: t for t in TOPICS}
TOPIC_SLUGS: frozenset[str] = frozenset(TOPICS_BY_SLUG)
