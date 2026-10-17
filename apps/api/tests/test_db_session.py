from app.db.session import ASYNCPG_CONNECT_ARGS, build_engine


def test_statement_cache_disabled_for_pooler() -> None:
    assert ASYNCPG_CONNECT_ARGS == {"statement_cache_size": 0}


def test_engine_uses_asyncpg() -> None:
    engine = build_engine("postgresql+asyncpg://user:pw@localhost:5432/db")
    assert engine.dialect.driver == "asyncpg"
