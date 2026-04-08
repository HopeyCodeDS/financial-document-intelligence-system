"""
Pydantic schemas for audit log API responses.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.audit_log import AuditEventCategory, AuditEventStatus


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID | None
    event_type: str
    event_category: AuditEventCategory
    actor: str
    timestamp: datetime
    step_name: str | None
    duration_ms: int | None
    status: AuditEventStatus
    details: dict[str, Any]
    ip_address: str | None
    session_id: str | None

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
