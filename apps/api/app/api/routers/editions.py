"""Daily editions, the archive and the PDF download."""

import uuid
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import Response
from sqlalchemy import select

from app.api.deps import CurrentUser, EditionServiceDep, SessionDep, SettingsDep, current_user
from app.core.errors import AppError
from app.editions.service import local_date
from app.models import Edition, EditionStatus, EventType, ReaderEvent
from app.pdf.service import PDF_CONTENT_TYPE, pdf_filename, read_pdf, render_edition
from app.schemas.editions import EditionOut, EditionSummary, SavedItem
from app.schemas.stories import StoryOut
from app.services import editions as read
from app.storage import Storage, StorageError, default_storage

router = APIRouter(prefix="/editions", tags=["editions"], dependencies=[Depends(current_user)])


def get_storage_dep() -> Storage:
    return default_storage()


StorageDep = Annotated[Storage, Depends(get_storage_dep)]


def _today(user: CurrentUser) -> date:
    return local_date(user.timezone, datetime.now(UTC))


@router.get("", response_model=list[EditionSummary])
async def list_editions(
    user: CurrentUser,
    session: SessionDep,
    before: Annotated[date | None, Query(description="Only editions before this date")] = None,
    limit: Annotated[int, Query(ge=1, le=read.ARCHIVE_MAX_PAGE)] = read.ARCHIVE_PAGE,
) -> list[EditionSummary]:
    """The archive, newest first. A page shorter than ``limit`` is the last one."""
    return await read.list_archive(session, user.id, before=before, limit=limit)


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


@router.get(
    "/{edition_date}/pdf",
    response_class=Response,
    responses={200: {"content": {PDF_CONTENT_TYPE: {}}, "description": "The newspaper PDF"}},
)
async def download_pdf(
    edition_date: date,
    user: CurrentUser,
    session: SessionDep,
    settings: SettingsDep,
    storage: StorageDep,
) -> Response:
    """Stream the reader's PDF for a day (typesetting it first if it is missing or out of date)."""
    edition = (
        await session.execute(
            select(Edition).where(Edition.user_id == user.id, Edition.edition_date == edition_date)
        )
    ).scalar_one_or_none()
    if edition is None or edition.status is not EditionStatus.READY:
        raise AppError(404, "not_found", "There is no finished edition for that date")
    try:
        result = await render_edition(session, storage, settings, edition)
        data = await read_pdf(storage, result.path)
    except StorageError as exc:
        raise AppError(
            503, "storage_unavailable", "The PDF could not be fetched right now"
        ) from exc
    if data is None:
        raise AppError(503, "storage_unavailable", "The PDF could not be fetched right now")
    session.add(
        ReaderEvent(
            user_id=user.id,
            edition_id=edition.id,
            type=EventType.PDF_DOWNLOAD,
            meta={"bytes": len(data), "rendered_now": result.rendered},
        )
    )
    await session.commit()
    filename = pdf_filename(result.paper_name, edition_date)
    return Response(
        content=data,
        media_type=PDF_CONTENT_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


saved_router = APIRouter(tags=["editions"], dependencies=[Depends(current_user)])


@saved_router.get("/saved", response_model=list[SavedItem])
async def list_saved(user: CurrentUser, session: SessionDep) -> list[SavedItem]:
    """Stories the reader saved, from any edition."""
    return await read.list_saved(session, user.id)


story_router = APIRouter(prefix="/stories", tags=["editions"], dependencies=[Depends(current_user)])


@story_router.get("/{edition_item_id}", response_model=StoryOut)
async def get_story(edition_item_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> StoryOut:
    """One story from the reader's paper, with the pictures and outlets of the same story."""
    return await read.get_story(session, user.id, edition_item_id)
