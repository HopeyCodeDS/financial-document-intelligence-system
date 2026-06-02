"""
Authentication API endpoints.

POST /api/v1/auth/login    — exchange email + password for a JWT
POST /api/v1/auth/refresh  — re-issue a token if the current one is near expiry
GET  /api/v1/auth/me       — return the authenticated user's profile

These endpoints are intentionally narrow. Anything that mutates user records
(create, deactivate, role change) is reserved for an admin surface that does
not exist yet — designed so it can be added without changing this module.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.security import create_access_token
from app.db.session import get_db_session
from app.dependencies import CurrentUserId, get_app_settings
from app.schemas.user import LoginRequest, LoginResponse, MeResponse, UserPublic
from app.services.auth.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Auth"])


def _client_ip(request: Request) -> str | None:
    """Best-effort client IP. Trusts the immediate peer; behind a proxy
    the request_context middleware will already have logged the X-Forwarded-For
    chain — we don't re-derive it here to avoid spoofing."""
    if request.client is None:
        return None
    return request.client.host


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Exchange email + password for a JWT access token",
)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> LoginResponse:
    service = UserService(db)
    user = await service.authenticate(
        email=str(payload.email),
        password=payload.password,
        ip_address=_client_ip(request),
    )
    if user is None:
        await db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        subject=str(user.id),
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_minutes=settings.jwt_access_token_expire_minutes,
        extra_claims={"role": user.role.value, "email": user.email},
    )
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in_seconds=settings.jwt_access_token_expire_minutes * 60,
        user=UserPublic.model_validate(user),
    )


@router.post(
    "/refresh",
    response_model=LoginResponse,
    summary="Re-issue a JWT for the current user",
)
async def refresh(
    current_user_id: CurrentUserId,
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> LoginResponse:
    """
    Re-issue using the existing token's identity.
    """
    service = UserService(db)
    user = await service.get_by_id(uuid.UUID(current_user_id))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer active",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        subject=str(user.id),
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_minutes=settings.jwt_access_token_expire_minutes,
        extra_claims={"role": user.role.value, "email": user.email},
    )
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in_seconds=settings.jwt_access_token_expire_minutes * 60,
        user=UserPublic.model_validate(user),
    )


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Return the authenticated user's profile",
)
async def me(
    current_user_id: CurrentUserId,
    db: AsyncSession = Depends(get_db_session),
) -> MeResponse:
    service = UserService(db)
    user = await service.get_by_id(uuid.UUID(current_user_id))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer active",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return MeResponse.model_validate(user)
