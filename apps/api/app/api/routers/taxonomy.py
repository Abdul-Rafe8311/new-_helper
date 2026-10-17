"""Topic taxonomy used by onboarding and profiles."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.taxonomy import TOPICS, TopicGroup

router = APIRouter(tags=["taxonomy"])


class TopicOut(BaseModel):
    slug: str
    label: str
    group: TopicGroup
    description: str


class TaxonomyOut(BaseModel):
    groups: list[TopicGroup]
    topics: list[TopicOut]


@router.get("/taxonomy")
async def get_taxonomy() -> TaxonomyOut:
    return TaxonomyOut(
        groups=list(TopicGroup),
        topics=[
            TopicOut(slug=t.slug, label=t.label, group=t.group, description=t.description)
            for t in TOPICS
        ],
    )
