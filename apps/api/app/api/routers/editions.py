"""Daily editions and the archive. Implemented in T8-T10."""

from datetime import date

from fastapi import APIRouter, Depends

from app.api.deps import current_user
from app.core.errors import AppError

router = APIRouter(prefix="/editions", tags=["editions"], dependencies=[Depends(current_user)])

_NOT_YET = AppError(501, "not_implemented", "Editions are not available yet")


@router.get("")
async def list_editions() -> None:
    raise _NOT_YET


@router.get("/{edition_date}")
async def get_edition(edition_date: date) -> None:
    raise _NOT_YET
