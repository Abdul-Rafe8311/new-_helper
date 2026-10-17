import pytest

from app.core.config import Settings


@pytest.mark.parametrize(
    "scheme", ["postgres", "postgresql", "postgresql+psycopg", "postgresql+psycopg2"]
)
def test_database_url_is_forced_to_asyncpg(scheme: str) -> None:
    settings = Settings(database_url=f"{scheme}://user:pw@host:5432/db")
    assert settings.database_url == "postgresql+asyncpg://user:pw@host:5432/db"


def test_asyncpg_url_is_unchanged() -> None:
    url = "postgresql+asyncpg://user:pw@host:5432/db"
    assert Settings(database_url=url).database_url == url
