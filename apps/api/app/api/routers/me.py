"""The signed-in reader's own profile."""

from datetime import UTC, datetime

from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.editions.service import local_date
from app.schemas.profile import ProfileOut, ProfileUpdate
from app.schemas.quiz import QuizStreakOut
from app.services import profile as profile_service
from app.services import quiz as quiz_service

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/profile")
async def get_profile(user: CurrentUser) -> ProfileOut:
    return ProfileOut.model_validate(user.profile)


@router.put("/profile")
async def put_profile(body: ProfileUpdate, user: CurrentUser, session: SessionDep) -> ProfileOut:
    profile = await profile_service.update_profile(session, user.profile, body)
    return ProfileOut.model_validate(profile)


@router.get("/quiz-streak")
async def get_quiz_streak(user: CurrentUser, session: SessionDep) -> QuizStreakOut:
    today = local_date(user.timezone, datetime.now(UTC))
    return await quiz_service.quiz_streak(session, user.id, today)
