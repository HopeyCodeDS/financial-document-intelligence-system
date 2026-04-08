"""
AuditLog ORM model — immutable append-only event log.

IMPORTANT: No UPDATE or DELETE operations are permitted on this table.
This is enforced at two levels:
  1. DB trigger: prevent_audit_log_mutation() defined in docker/postgres/init.sql
     and attached in alembic/versions/001_initial_schema.py
  2. Application: AuditLogRepository only exposes insert/query — no update/delete methods.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import DateTime, func
from datetime import UTC, datetime

from app.models.base import Base, UUIDMixin


class AuditEventCategory(str, enum.Enum):
    pipeline = "pipeline"
    security = "security"
    review = "review"
    system = "system"
    api = "api"


class AuditEventStatus(str, enum.Enum):
    success = "success"
    failure = "failure"
    warning = "warning"


class AuditLog(Base, UUIDMixin):
    """
    Append-only audit record.

    No TimestampMixin — timestamp is set once at insert and must never change.
    There is intentionally no updated_at column.
    """
    __tablename__ = "audit_logs"

    # Document reference — nullable for system-level events
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    # Event classification
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_category: Mapped[AuditEventCategory] = mapped_column(
        Enum(AuditEventCategory, name="audit_event_category_enum"),
        nullable=False,
        index=True,
    )

    # Actor (user_id or "system")
    actor: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Timing — set once at creation, never updated
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    step_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Outcome
    status: Mapped[AuditEventStatus] = mapped_column(
        Enum(AuditEventStatus, name="audit_event_status_enum"),
        nullable=False,
    )

    # Structured payload — must NOT contain raw PII
    details: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    # Request context
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv6 max
    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Soft FK to document (not a real FK to allow orphaned system events)
    document: Mapped["Document | None"] = relationship(  # noqa: F821
        "Document",
        primaryjoin="AuditLog.document_id == Document.id",
        foreign_keys="[AuditLog.document_id]",
        back_populates="audit_logs",
        viewonly=True,
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} event={self.event_type} "
            f"actor={self.actor} status={self.status}>"
        )
