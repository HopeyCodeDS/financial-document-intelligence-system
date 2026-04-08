"""
FastAPI dependency injection providers.

All shared resources (DB session, settings, current user) are declared here
so they can be overridden in tests via app.dependency_overrides.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.exceptions import AuthenticationError
from app.core.security import decode_access_token
from app.db.session import get_db_session

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

    Raises HTTP 401 if the token is missing or invalid.
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


CurrentUser = Annotated[str, Depends(get_current_user)]
