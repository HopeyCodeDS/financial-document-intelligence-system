"""
ORM model registry.

Importing this package loads every model so SQLAlchemy's mapper registry is
complete before the first query compiles. Without this, code paths that
touch only one model (e.g. ``/auth/login`` querying only ``User``) fail at
mapper-configure time when an unrelated model declares a string-named
relationship the registry hasn't seen yet (e.g. ``Document → PIIMapping``).
"""
from __future__ import annotations

from app.models.audit_log import AuditEventCategory, AuditEventStatus, AuditLog
from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.extraction import ExtractionResult, RiskLevel, ValidationStatus
from app.models.pii_mapping import PIIMapping
from app.models.review import (
    ReviewDecision,
    ReviewDecisionType,
    ReviewPriority,
    ReviewTask,
    ReviewTaskStatus,
)
from app.models.user import User, UserRole

__all__ = [
    "AuditEventCategory",
    "AuditEventStatus",
    "AuditLog",
    "Base",
    "Document",
    "DocumentStatus",
    "DocumentType",
    "ExtractionResult",
    "PIIMapping",
    "ReviewDecision",
    "ReviewDecisionType",
    "ReviewPriority",
    "ReviewTask",
    "ReviewTaskStatus",
    "RiskLevel",
    "TimestampMixin",
    "UUIDMixin",
    "User",
    "UserRole",
    "ValidationStatus",
]
