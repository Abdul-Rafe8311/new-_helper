"""Email + password sessions held in an httpOnly cookie."""

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, SessionDep, SettingsDep
from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import SESSION_COOKIE, create_session_token
from app.models import User
from app.schemas.auth import LoginIn, RegisterIn, UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def to_user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        timezone=user.timezone,
        city=user.city,
        onboarding_completed=user.profile.onboarding_completed,
    )


def _start_session(response: Response, user: User, settings: Settings) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(user.id, settings),
        max_age=settings.jwt_expiry_days * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.env == "prod",
        path="/",
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterIn, response: Response, session: SessionDep, settings: SettingsDep
) -> UserOut:
    user = await auth_service.register_user(
        session,
        email=body.email,
        password=body.password,
        display_name=body.display_name,
        timezone=body.timezone,
        city=body.city,
    )
    _start_session(response, user, settings)
    return to_user_out(user)


@router.post("/login")
async def login(
    body: LoginIn, response: Response, session: SessionDep, settings: SettingsDep
) -> UserOut:
    user = await auth_service.authenticate(session, body.email, body.password)
    if user is None:
        raise AppError(401, "invalid_credentials", "Email or password is incorrect")
    _start_session(response, user, settings)
    return to_user_out(user)


@router.post("/demo")
async def demo(response: Response, session: SessionDep, settings: SettingsDep) -> UserOut:
    user = await auth_service.get_user_by_email(session, settings.demo_email)
    if user is None:
        raise AppError(503, "demo_unavailable", "The demo account has not been set up yet")
    _start_session(response, user, settings)
    return to_user_out(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, settings: SettingsDep) -> None:
    response.delete_cookie(
        SESSION_COOKIE, path="/", httponly=True, samesite="lax", secure=settings.env == "prod"
    )


@router.get("/me")
async def me(user: CurrentUser) -> UserOut:
    return to_user_out(user)
