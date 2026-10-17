"""Daily editions and the archive. The list/read endpoints arrive in T10; the PDF is here."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select

from app.api.deps import CurrentUser, SessionDep, SettingsDep, current_user
from app.core.errors import AppError
from app.models import Edition, EditionStatus, EventType, ReaderEvent
from app.pdf.service import PDF_CONTENT_TYPE, pdf_filename, read_pdf, render_edition
from app.storage import Storage, StorageError, default_storage

router = APIRouter(prefix="/editions", tags=["editions"], dependencies=[Depends(current_user)])

_NOT_YET = AppError(501, "not_implemented", "Editions are not available yet")


def get_storage_dep() -> Storage:
    return default_storage()


StorageDep = Annotated[Storage, Depends(get_storage_dep)]


@router.get("")
async def list_editions() -> None:
    raise _NOT_YET


@router.get("/{edition_date}")
async def get_edition(edition_date: date) -> None:
    raise _NOT_YET


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
