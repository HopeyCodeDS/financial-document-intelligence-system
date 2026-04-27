"""
Audit log query API endpoints.

GET /api/v1/audit/              — query audit events (filtered)
GET /api/v1/audit/{document_id} — all events for a specific document
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.audit_log import AuditLogRepository
from app.db.session import get_db_session
from app.dependencies import get_current_user
from app.schemas.audit import AuditLogListResponse, AuditLogResponse

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/", response_model=AuditLogListResponse, summary="Query audit events")
async def query_audit_log(
    document_id: uuid.UUID | None = Query(default=None),
    event_type: str | None = Query(default=None),
    actor: str | None = Query(default=None),
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(get_current_user),
) -> AuditLogListResponse:
    repo = AuditLogRepository(db)
    offset = (page - 1) * page_size
    items, total = await repo.query(
        document_id=document_id,
        event_type=event_type,
        actor=actor,
        since=since,
        until=until,
        offset=offset,
        limit=page_size,
    )
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/document/{document_id}",
    response_model=AuditLogListResponse,
    summary="Get all audit events for a document",
)
async def get_document_audit_trail(
    document_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(get_current_user),
) -> AuditLogListResponse:
    repo = AuditLogRepository(db)
    offset = (page - 1) * page_size
    items, total = await repo.query(
        document_id=document_id,
        offset=offset,
        limit=page_size,
    )
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
    )
