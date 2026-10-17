"""Load and validate the curated source registry (registry.yaml)."""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator

from app.core.taxonomy import TOPIC_SLUGS
from app.models import SourceKind

REGISTRY_PATH = Path(__file__).with_name("registry.yaml")


class SourceSpec(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    kind: SourceKind
    url: str = Field(pattern=r"^https?://")
    topics: list[str] = Field(min_length=1)
    quality: float = Field(default=0.5, ge=0, le=1)

    @field_validator("topics")
    @classmethod
    def known_topics(cls, value: list[str]) -> list[str]:
        if unknown := sorted(set(value) - TOPIC_SLUGS):
            raise ValueError(f"unknown topics: {', '.join(unknown)}")
        return value


class Registry(BaseModel):
    sources: list[SourceSpec]

    @field_validator("sources")
    @classmethod
    def unique_urls(cls, value: list[SourceSpec]) -> list[SourceSpec]:
        urls = [s.url for s in value]
        if dupes := sorted({u for u in urls if urls.count(u) > 1}):
            raise ValueError(f"duplicate urls: {', '.join(dupes)}")
        return value


def load_registry(path: Path = REGISTRY_PATH) -> list[SourceSpec]:
    return Registry.model_validate(yaml.safe_load(path.read_text())).sources
