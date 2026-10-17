"""Account creation and credential checks."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.core.security import hash_password, verify_password
from app.models import ReaderProfile, User


def normalise_email(email: str) -> str:
    return email.strip().lower()


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(
        select(User).options(selectinload(User.profile)).where(User.email == normalise_email(email))
    )
    return result.scalar_one_or_none()


async def register_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    display_name: str,
    timezone: str = "Asia/Karachi",
    city: str | None = None,
) -> User:
    email = normalise_email(email)
    if await get_user_by_email(session, email) is not None:
        raise AppError(409, "email_taken", "An account with this email already exists")
    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name=display_name.strip(),
        timezone=timezone,
        city=city,
        profile=ReaderProfile(),
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:  # lost a race with a concurrent signup
        await session.rollback()
        raise AppError(409, "email_taken", "An account with this email already exists") from exc
    return user


async def authenticate(session: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user_by_email(session, email)
    if not verify_password(password, user.password_hash if user else None):
        return None
    return user
