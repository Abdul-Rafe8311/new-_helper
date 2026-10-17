"""Application settings, loaded from environment variables (and .env in dev)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_URL = "https://github.com/Abdul-Rafe8311/new-_helper"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "NewsHelper"
    env: Literal["dev", "test", "prod"] = "dev"
    version: str = "0.1.0"
    git_sha: str = "dev"
    log_level: str = "INFO"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    web_url: str = "http://localhost:3000"

    # Database
    database_url: str = "postgresql+asyncpg://newshelper:newshelper@localhost:5432/newshelper"

    # Storage
    storage_backend: Literal["local", "supabase"] = "local"
    storage_local_dir: str = "./.storage"
    supabase_url: str = ""
    supabase_service_key: SecretStr = SecretStr("")
    supabase_bucket: str = "editions"

    # PDF edition
    pdf_page_size: Literal["A4", "Letter"] = "A4"

    # Auth & internal
    jwt_secret: SecretStr = SecretStr("dev-insecure-jwt-secret-change-me-in-env")
    jwt_expiry_days: int = 7
    cron_secret: SecretStr = SecretStr("dev-cron-secret")
    demo_email: str = "demo@newshelper.app"

    # AI
    anthropic_api_key: SecretStr = SecretStr("")
    llm_fast_model: str = "claude-haiku-5-5"
    llm_smart_model: str = "claude-sonnet-5-5"
    llm_daily_budget_usd: float = 2.0
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    fastembed_cache_dir: str = "~/.cache/fastembed"

    # Scraping
    user_agent: str = f"NewsHelperBot/0.1 (+{REPO_URL})"
    allowed_languages: list[str] = Field(default_factory=lambda: ["en"])
    reddit_enabled: bool = False
    reddit_subreddits: list[str] = Field(
        default_factory=lambda: ["worldnews", "technology", "science"]
    )
    apify_token: SecretStr = SecretStr("")
    apify_gnews_actor: str = "hiver/google-news-scraper"
    apify_extract_actor: str = "apify/website-content-crawler"

    # Audio
    elevenlabs_api_key: SecretStr = SecretStr("")

    @field_validator("database_url")
    @classmethod
    def _use_asyncpg_driver(cls, value: str) -> str:
        """Accept the URL as copied from Supabase (postgres://, postgresql://, +psycopg)."""
        for prefix in (
            "postgres://",
            "postgresql://",
            "postgresql+psycopg://",
            "postgresql+psycopg2://",
        ):
            if value.startswith(prefix):
                return "postgresql+asyncpg://" + value[len(prefix) :]
        return value

    @property
    def apify_enabled(self) -> bool:
        return bool(self.apify_token.get_secret_value())


@lru_cache
def get_settings() -> Settings:
    return Settings()
