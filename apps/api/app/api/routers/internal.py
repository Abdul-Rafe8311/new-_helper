"""Machine-only routes (scheduled jobs), guarded by the X-Cron-Secret header."""

from fastapi import APIRouter, Depends

from app.api.deps import require_cron_secret

router = APIRouter(
    prefix="/internal", tags=["internal"], dependencies=[Depends(require_cron_secret)]
)


@router.get("/ping")
async def ping() -> dict[str, bool]:
    return {"ok": True}
