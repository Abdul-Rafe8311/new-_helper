"""FastAPI entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import (
    auth,
    editions,
    events,
    interests,
    internal,
    me,
    onboarding,
    redirect,
    taxonomy,
)
from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestIDMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)
    app = FastAPI(title=f"{settings.app_name} API", version=settings.version)

    app.dependency_overrides[get_settings] = lambda: settings

    register_error_handlers(app)
    app.add_middleware(RequestIDMiddleware)
    # In prod the web app proxies /api/* to us, so requests are same-origin and need no CORS.
    if settings.env == "dev":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": settings.version, "git_sha": settings.git_sha}

    for module in (auth, me, interests, onboarding, editions, events, redirect, internal, taxonomy):
        app.include_router(module.router)
    app.include_router(editions.saved_router)
    app.include_router(editions.story_router)
    return app


app = create_app()
