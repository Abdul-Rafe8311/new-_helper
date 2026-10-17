"""Daily editions and the archive."""

from datetime import UTC, date, datetime

from fastapi import APIRouter, BackgroundTasks, Depends

from app.api.deps import CurrentUser, EditionServiceDep, SessionDep, current_user
from app.editions.service import local_date
from app.schemas.editions import EditionOut, EditionSummary
from app.services import editions as read

router = APIRouter(prefix="/editions", tags=["editions"], dependencies=[Depends(current_user)])


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
    service: EditionServiceDep,
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
