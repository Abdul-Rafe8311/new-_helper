from fastapi.testclient import TestClient

from app.core.taxonomy import TOPICS, TopicGroup
from app.main import app


def test_taxonomy_slugs_unique_and_grouped() -> None:
    slugs = [t.slug for t in TOPICS]
    assert len(slugs) == len(set(slugs))
    assert 28 <= len(slugs) <= 40
    assert {t.group for t in TOPICS} == set(TopicGroup)


def test_get_taxonomy() -> None:
    response = TestClient(app).get("/taxonomy")
    assert response.status_code == 200
    body = response.json()
    assert body["groups"] == [g.value for g in TopicGroup]
    cricket = next(t for t in body["topics"] if t["slug"] == "cricket")
    assert cricket["group"] == "Sport"
    assert cricket["description"]
