from app.core.catalogue import (
    CATALOGUE,
    CATALOGUE_BY_SLUG,
    DEFAULT_ADD_WEIGHT,
    Section,
)
from app.core.taxonomy import TOPICS

# The keys profiles already hold. Never remove or rename one: saved weights are stored under them.
ORIGINAL_KEYS = [
    *("world", "pakistan", "south-asia", "middle-east", "us-politics", "europe"),
    *("business", "markets", "economy", "startups", "crypto", "personal-finance"),
    *("tech", "ai", "software", "cybersecurity", "gadgets"),
    *("science", "space", "health", "climate", "energy"),
    *("food", "travel", "education", "careers"),
    *("cricket", "football", "f1", "sports"),
    *("film-tv", "music", "books", "design", "gaming"),
]


def test_existing_keys_are_unchanged() -> None:
    assert [t.slug for t in TOPICS] == ORIGINAL_KEYS
    for original in TOPICS:
        topic = CATALOGUE_BY_SLUG[original.slug]
        assert (topic.label, topic.description) == (original.label, original.description)


def test_catalogue_is_large_unique_and_sectioned() -> None:
    slugs = [t.slug for t in CATALOGUE]
    assert len(slugs) == len(set(slugs)) >= 40
    assert {t.section for t in CATALOGUE} == set(Section)
    assert [s.value for s in Section] == [
        "Technology",
        "Science",
        "World",
        "Pakistan",
        "Business and Markets",
        "Sport",
        "Culture",
        "Health",
        "Climate",
        "Entertainment",
    ]
    assert all(t.label and t.description for t in CATALOGUE)


def test_a_new_topic_starts_below_full_weight() -> None:
    assert 0 < DEFAULT_ADD_WEIGHT < 1
