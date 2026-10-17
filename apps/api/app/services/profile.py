"""Reader profile reads and edits."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ReaderProfile
from app.schemas.profile import ProfileUpdate

_NULLABLE = {"paper_name", "context_notes"}


async def update_profile(
    session: AsyncSession, profile: ReaderProfile, changes: ProfileUpdate
) -> ReaderProfile:
    for field, value in changes.model_dump(exclude_unset=True).items():
        if value is None and field not in _NULLABLE:
            continue
        if field == "paper_name" and value == "":
            value = None
        setattr(profile, field, value)
    await session.commit()
    await session.refresh(profile)
    return profile
