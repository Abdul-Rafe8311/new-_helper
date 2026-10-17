"""FastAPI entrypoint."""

from fastapi import FastAPI

from app.api.routers import taxonomy
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=f"{settings.app_name} API", version=settings.version)

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": settings.version, "git_sha": settings.git_sha}

    app.include_router(taxonomy.router)
    return app


app = create_app()
