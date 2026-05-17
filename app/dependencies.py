"""
FastAPI dependency injection providers.

All shared resources (DB session, settings, current user) are declared here
so they can be overridden in tests via app.dependency_overrides.

Two flavours of "current user" are exposed:

- ``get_current_user`` (and the ``CurrentUserId`` alias) returns the JWT
  subject as a string. Use this when only the actor identity is needed —
  no DB round-trip.
- ``get_current_user_record`` (and the ``CurrentUser`` alias) hydrates the
  full ``User`` ORM record. Use this when role, email, or active status
  must be checked.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.exceptions import AuthenticationError
from app.core.security import decode_access_token
from app.db.session import get_db_session
from app.models.user import User

# ── Settings ──────────────────────────────────────────────────────────────────

def get_app_settings() -> Settings:
    return get_settings()

SettingsDep = Annotated[Settings, Depends(get_app_settings)]

# ── Database ──────────────────────────────────────────────────────────────────

DbSession = Annotated[AsyncSession, Depends(get_db_session)]

# ── Auth ──────────────────────────────────────────────────────────────────────

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_app_settings),
) -> str:
    """Validate JWT and return the subject (user_id string).

    Raises HTTP 401 if the token is missing or invalid. Does NOT touch the DB —
    use ``get_current_user_record`` when you need the full User row.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(
            credentials.credentials,
            settings.jwt_secret_key,
            settings.jwt_algorithm,
        )
        user_id: str = payload["sub"]
        return user_id
    except (AuthenticationError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


CurrentUserId = Annotated[str, Depends(get_current_user)]


async def get_current_user_record(
    current_user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Hydrate the full ``User`` record for the JWT subject.

    Rejects the request if the user has been deactivated since the token was
    issued — keeps tokens revocable without an explicit blocklist.
    """
    try:
        user_uuid = uuid.UUID(current_user_id)
    except ValueError as exc:
        # Tokens minted before the users-table migration carried opaque
        # subject strings. Those are no longer valid identities.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject is not a known user",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await db.get(User, user_uuid)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer active",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user_record)]
