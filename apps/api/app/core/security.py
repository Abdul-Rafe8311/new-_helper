"""Password hashing (argon2 via pwdlib) and session JWTs (HS256)."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import Settings

SESSION_COOKIE = "dp_session"
JWT_ALGORITHM = "HS256"

_hasher = PasswordHash((Argon2Hasher(),))
# Verified against when the email is unknown, so login timing doesn't reveal which emails exist.
_DUMMY_HASH = _hasher.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        _hasher.verify(password, _DUMMY_HASH)
        return False
    try:
        return _hasher.verify(password, password_hash)
    except Exception:  # malformed / unusable hash
        return False


def create_session_token(user_id: uuid.UUID, settings: Settings) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_expiry_days),
    }
    return jwt.encode(claims, settings.jwt_secret.get_secret_value(), algorithm=JWT_ALGORITHM)


def decode_session_token(token: str, settings: Settings) -> uuid.UUID | None:
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp"]},
        )
        return uuid.UUID(claims["sub"])
    except (jwt.PyJWTError, ValueError):
        return None
