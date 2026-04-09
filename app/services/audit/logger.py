"""
AuditLogger — structured, append-only event writer.

Design contract:
- Every call to log() writes a record to the audit_log table.
- log() never raises — failures are caught and reported via structlog only.
  This prevents audit failures from masking the original business error.
- Records are immutable after insert (enforced by DB trigger).
- PII must NEVER appear in the details payload.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditEventCategory, AuditEventStatus, AuditLog

logger = structlog.get_logger(__name__)


class AuditLogger:
    """Async audit event writer bound to a DB session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log(
        self,
        event_type: str,
        category: AuditEventCategory,
        actor: str,
        status: AuditEventStatus,
        document_id: uuid.UUID | None = None,
        step_name: str | None = None,
        duration_ms: int | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        session_id: str | None = None,
    ) -> None:
        """
        Append a single audit event.

        Never raises. PII must not appear in details.
        """
        try:
            event = AuditLog(
                document_id=document_id,
                event_type=event_type,
                event_category=category,
                actor=actor,
                timestamp=datetime.now(UTC),
                step_name=step_name,
                duration_ms=duration_ms,
                status=status,
                details=details or {},
                ip_address=ip_address,
                session_id=session_id,
            )
            self._session.add(event)
            await self._session.flush()
        except Exception as exc:
            # Must not propagate — audit failure should never mask business logic
            logger.exception(
                "audit_log_write_failed",
                event_type=event_type,
                document_id=str(document_id) if document_id else None,
                error=str(exc),
            )

    async def log_pipeline_step(
        self,
        document_id: uuid.UUID,
        step_name: str,
        status: AuditEventStatus,
        actor: str = "system",
        duration_ms: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Convenience method for pipeline step events."""
        await self.log(
            event_type=f"pipeline.step.{step_name}",
            category=AuditEventCategory.pipeline,
            actor=actor,
            status=status,
            document_id=document_id,
            step_name=step_name,
            duration_ms=duration_ms,
            details=details,
        )

    async def log_api_event(
        self,
        event_type: str,
        actor: str,
        status: AuditEventStatus,
        document_id: uuid.UUID | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        session_id: str | None = None,
    ) -> None:
        """Convenience method for API-layer events (upload, review decisions, etc.)."""
        await self.log(
            event_type=event_type,
            category=AuditEventCategory.api,
            actor=actor,
            status=status,
            document_id=document_id,
            details=details,
            ip_address=ip_address,
            session_id=session_id,
        )

    async def log_security_event(
        self,
        event_type: str,
        actor: str,
        status: AuditEventStatus,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> None:
        """Convenience method for security events (auth failures, PII leaks, etc.)."""
        await self.log(
            event_type=event_type,
            category=AuditEventCategory.security,
            actor=actor,
            status=status,
            details=details,
            ip_address=ip_address,
        )
