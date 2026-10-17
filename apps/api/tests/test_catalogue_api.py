from fastapi.testclient import TestClient

from app.core.catalogue import CATALOGUE
from app.core.taxonomy import TOPIC_SLUGS
from app.main import app
from app.sources.registry import load_registry

client = TestClient(app)


def test_topic_catalogue_is_public_and_includes_the_onboarding_keys() -> None:
    response = client.get("/catalogue/topics")
    assert response.status_code == 200
    body = response.json()
    slugs = {t["slug"] for t in body["topics"]}
    assert slugs >= TOPIC_SLUGS
    assert len(body["topics"]) == len(CATALOGUE) >= 40
    assert {t["section"] for t in body["topics"]} == set(body["sections"])
    assert 0 < body["default_weight"] < 1
    climate = next(t for t in body["topics"] if t["slug"] == "climate")
    assert climate["section"] == "Climate"


def test_source_catalogue_lists_every_registry_source_under_a_section() -> None:
    body = client.get("/catalogue/sources").json()
    assert [s["name"] for s in body["sources"]] == [s.name for s in load_registry()]
    assert {s["section"] for s in body["sources"]} <= set(body["sections"])
    dawn = next(s for s in body["sources"] if s["name"] == "Dawn")
    assert dawn["section"] == "Pakistan"
