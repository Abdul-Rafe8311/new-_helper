"""The public, read-only catalogue the interests page browses: topics and sources."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.catalogue import CATALOGUE, CATALOGUE_BY_SLUG, DEFAULT_ADD_WEIGHT, Section
from app.sources.registry import load_registry

router = APIRouter(prefix="/catalogue", tags=["catalogue"])


class CatalogueTopicOut(BaseModel):
    slug: str
    label: str
    section: Section
    description: str


class TopicCatalogueOut(BaseModel):
    sections: list[Section]
    topics: list[CatalogueTopicOut]
    # where a topic starts when a reader adds it: what onboarding gives a topic they picked
    default_weight: float


class CatalogueSourceOut(BaseModel):
    name: str
    section: Section
    topics: list[str]


class SourceCatalogueOut(BaseModel):
    sections: list[Section]
    sources: list[CatalogueSourceOut]


@router.get("/topics")
async def get_topics() -> TopicCatalogueOut:
    return TopicCatalogueOut(
        sections=list(Section),
        topics=[
            CatalogueTopicOut(
                slug=t.slug, label=t.label, section=t.section, description=t.description
            )
            for t in CATALOGUE
        ],
        default_weight=DEFAULT_ADD_WEIGHT,
    )


@router.get("/sources")
async def get_sources() -> SourceCatalogueOut:
    """The registry's sources, each filed under the section of its first topic."""
    sources = [
        CatalogueSourceOut(
            name=s.name, section=CATALOGUE_BY_SLUG[s.topics[0]].section, topics=s.topics
        )
        for s in load_registry()
    ]
    return SourceCatalogueOut(sections=list(Section), sources=sources)
