"""The signed-in reader's own profile."""

from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.schemas.profile import ProfileOut, ProfileUpdate
from app.services import profile as profile_service

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/profile")
async def get_profile(user: CurrentUser) -> ProfileOut:
    return ProfileOut.model_validate(user.profile)


@router.put("/profile")
async def put_profile(body: ProfileUpdate, user: CurrentUser, session: SessionDep) -> ProfileOut:
    profile = await profile_service.update_profile(session, user.profile, body)
    return ProfileOut.model_validate(profile)
