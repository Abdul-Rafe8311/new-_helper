import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import Settings
from app.core.security import (
    create_session_token,
    decode_session_token,
    hash_password,
    verify_password,
)

SECRET = "t" * 32
SETTINGS = Settings(jwt_secret=SECRET, jwt_expiry_days=7)


def test_password_round_trip() -> None:
    hashed = hash_password("correct horse")
    assert hashed.startswith("$argon2")
    assert verify_password("correct horse", hashed)
    assert not verify_password("wrong", hashed)


def test_unknown_user_and_bad_hash_never_verify() -> None:
    assert not verify_password("anything", None)
    assert not verify_password("anything", "not-a-hash")


def test_session_token_round_trip_and_expiry() -> None:
    user_id = uuid.uuid4()
    token = create_session_token(user_id, SETTINGS)
    assert decode_session_token(token, SETTINGS) == user_id
    claims = jwt.decode(token, SECRET, algorithms=["HS256"])
    assert claims["exp"] - claims["iat"] == 7 * 24 * 3600


def test_rejects_tampered_expired_and_foreign_tokens() -> None:
    token = create_session_token(uuid.uuid4(), SETTINGS)
    assert decode_session_token(token, Settings(jwt_secret="x" * 32)) is None
    assert decode_session_token(token[:-2] + "xx", SETTINGS) is None
    past = datetime.now(UTC) - timedelta(days=1)
    expired = jwt.encode({"sub": str(uuid.uuid4()), "exp": past}, SECRET, algorithm="HS256")
    assert decode_session_token(expired, SETTINGS) is None
    none_alg = jwt.encode({"sub": str(uuid.uuid4()), "exp": past + timedelta(days=9)}, None, "none")
    assert decode_session_token(none_alg, SETTINGS) is None
