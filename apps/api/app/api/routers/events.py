"""Reader behaviour events feeding the learning loop. Implemented in T10-T11."""

from fastapi import APIRouter, Depends

from app.api.deps import current_user
from app.core.errors import AppError

router = APIRouter(prefix="/events", tags=["events"], dependencies=[Depends(current_user)])


@router.post("")
async def record_events() -> None:
    raise AppError(501, "not_implemented", "Event tracking is not available yet")
