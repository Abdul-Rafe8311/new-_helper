"""Daily editions and the archive."""

from datetime import UTC, date, datetime
from typing import Annotated

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends

from app.ai.factory import build_llm
from app.ai.usage import BudgetGuard
from app.api.deps import CurrentUser, SessionDep, SettingsDep, current_user
from app.db.session import get_sessionmaker
from app.editions.service import EditionService, local_date
from app.editions.weather import WeatherService
from app.schemas.editions import EditionOut, EditionSummary
from app.services import editions as read

router = APIRouter(prefix="/editions", tags=["editions"], dependencies=[Depends(current_user)])

_services: dict[str, EditionService] = {}


def get_edition_service(settings: SettingsDep) -> EditionService:
    """One service per process: it owns the Anthropic client and the weather HTTP client."""
    if "service" not in _services:
        sessionmaker = get_sessionmaker()
        _services["service"] = EditionService(
            sessionmaker,
            build_llm(settings, sessionmaker),
            settings.llm_smart_model,
            weather=WeatherService(
                httpx.AsyncClient(timeout=10.0, headers={"User-Agent": settings.user_agent})
            ),
            guard=BudgetGuard(sessionmaker, settings.llm_daily_budget_usd),
        )
    return _services["service"]


ServiceDep = Annotated[EditionService, Depends(get_edition_service)]


def _today(user: CurrentUser) -> date:
    return local_date(user.timezone, datetime.now(UTC))


@router.get("", response_model=list[EditionSummary])
async def list_editions(user: CurrentUser, session: SessionDep) -> list[EditionSummary]:
    return await read.list_archive(session, user.id)


@router.get("/today", response_model=EditionOut)
async def get_today(user: CurrentUser, session: SessionDep) -> EditionOut:
    return await read.get_edition_out(session, user.id, _today(user))


@router.post("/today/regenerate", response_model=EditionOut, status_code=202)
async def regenerate_today(
    user: CurrentUser,
    session: SessionDep,
    service: ServiceDep,
    background: BackgroundTasks,
) -> EditionOut:
    """Start (or restart) building today's paper and return at once; poll GET /editions/today.

    Limited to 3 regenerations a day. A paper that is already being built is left alone."""
    prepared = await service.prepare(session, user.id, _today(user), force=True)
    if prepared.needs_build:
        background.add_task(service.run, prepared.edition.id)
    return await read.to_out(session, prepared.edition)


@router.get("/{edition_date}", response_model=EditionOut)
async def get_edition(edition_date: date, user: CurrentUser, session: SessionDep) -> EditionOut:
    return await read.get_edition_out(session, user.id, edition_date)
