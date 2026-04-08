"""
JWT creation/verification and password hashing utilities.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.exceptions import AuthenticationError

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def create_access_token(
    subject: str,
    secret_key: str,
    algorithm: str,
    expires_minutes: int,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decode_access_token(
    token: str,
    secret_key: str,
    algorithm: str,
) -> dict[str, Any]:
    try:
        payload: dict[str, Any] = jwt.decode(token, secret_key, algorithms=[algorithm])
        return payload
    except JWTError as exc:
        raise AuthenticationError(f"Invalid or expired token: {exc}") from exc
