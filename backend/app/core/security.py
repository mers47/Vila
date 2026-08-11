from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings

_password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
ALGORITHM = "HS512"


@dataclass(frozen=True)
class DecodedToken:
    subject: str
    token_type: str
    session_id: str
    jti: str
    expires_at: datetime


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bool(_password_hasher.verify(hashed, password))
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_password_rehash(hashed: str) -> bool:
    try:
        return _password_hasher.check_needs_rehash(hashed)
    except InvalidHashError:
        return True


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    *,
    session_id: str,
    jti: str | None = None,
) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    token_id = jti or uuid.uuid4().hex
    payload = {
        "sub": subject,
        "type": token_type,
        "sid": session_id,
        "jti": token_id,
        "iat": now,
        "nbf": now,
        "exp": now + expires_delta,
        "iss": s.jwt_issuer,
        "aud": s.jwt_audience,
    }
    return jwt.encode(payload, s.secret_key, algorithm=ALGORITHM)


def decode_token(token: str, expected_type: str) -> DecodedToken:
    s = get_settings()
    try:
        payload = jwt.decode(
            token,
            s.secret_key,
            algorithms=[ALGORITHM],
            issuer=s.jwt_issuer,
            audience=s.jwt_audience,
            options={"require": ["sub", "type", "sid", "jti", "iat", "nbf", "exp", "iss", "aud"]},
        )
    except jwt.PyJWTError as exc:
        raise ValueError("invalid token") from exc
    if payload.get("type") != expected_type:
        raise ValueError("invalid token type")
    exp = datetime.fromtimestamp(int(payload["exp"]), tz=timezone.utc)
    return DecodedToken(
        subject=str(payload["sub"]),
        token_type=str(payload["type"]),
        session_id=str(payload["sid"]),
        jti=str(payload["jti"]),
        expires_at=exp,
    )