"""
AuditLog repository — query-only (no update/delete — enforced by DB trigger).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditLogRepository:
    """Read-only repository for the audit log table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def query(
        self,
        document_id: uuid.UUID | None = None,
        event_type: str | None = None,
        actor: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[AuditLog], int]:
        from sqlalchemy import func

        q = select(AuditLog)
        count_q = select(func.count()).select_from(AuditLog)

        if document_id is not None:
            q = q.where(AuditLog.document_id == document_id)
            count_q = count_q.where(AuditLog.document_id == document_id)
        if event_type is not None:
            q = q.where(AuditLog.event_type == event_type)
            count_q = count_q.where(AuditLog.event_type == event_type)
        if actor is not None:
            q = q.where(AuditLog.actor == actor)
            count_q = count_q.where(AuditLog.actor == actor)
        if since is not None:
            q = q.where(AuditLog.timestamp >= since)
            count_q = count_q.where(AuditLog.timestamp >= since)
        if until is not None:
            q = q.where(AuditLog.timestamp <= until)
            count_q = count_q.where(AuditLog.timestamp <= until)

        total_result = await self._session.execute(count_q)
        total = total_result.scalar_one()

        result = await self._session.execute(
            q.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)
        )
        items = list(result.scalars().all())
        return items, total
