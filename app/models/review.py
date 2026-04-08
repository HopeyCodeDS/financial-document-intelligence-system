"""
ReviewTask and ReviewDecision ORM models — human-in-the-loop review queue.
"""
from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ReviewPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class ReviewTaskStatus(str, enum.Enum):
    pending = "pending"
    in_review = "in_review"
    approved = "approved"
    rejected = "rejected"
    escalated = "escalated"


class ReviewDecisionType(str, enum.Enum):
    approved = "approved"
    rejected = "rejected"
    escalated = "escalated"
    needs_correction = "needs_correction"


class ReviewTask(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "review_tasks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    extraction_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extraction_results.id", ondelete="CASCADE"),
        nullable=False,
    )

    priority: Mapped[ReviewPriority] = mapped_column(
        Enum(ReviewPriority, name="review_priority_enum"),
        nullable=False,
        default=ReviewPriority.medium,
    )
    trigger_reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ReviewTaskStatus] = mapped_column(
        Enum(ReviewTaskStatus, name="review_task_status_enum"),
        nullable=False,
        default=ReviewTaskStatus.pending,
        index=True,
    )

    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    due_by: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    document: Mapped["Document"] = relationship(  # noqa: F821
        "Document", back_populates="review_tasks"
    )
    extraction_result: Mapped["ExtractionResult"] = relationship(  # noqa: F821
        "ExtractionResult", back_populates="review_tasks"
    )
    decisions: Mapped[list["ReviewDecision"]] = relationship(
        "ReviewDecision", back_populates="review_task", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<ReviewTask id={self.id} doc={self.document_id} "
            f"priority={self.priority} status={self.status}>"
        )


class ReviewDecision(Base, UUIDMixin):
    __tablename__ = "review_decisions"

    review_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("review_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[str] = mapped_column(String(255), nullable=False)

    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    decision: Mapped[ReviewDecisionType] = mapped_column(
        Enum(ReviewDecisionType, name="review_decision_type_enum"),
        nullable=False,
    )

    # Optional reviewer overrides
    confidence_override: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Field-level corrections: {"field_name": {"original": ..., "corrected": ...}}
    corrections: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    review_task: Mapped[ReviewTask] = relationship(
        "ReviewTask", back_populates="decisions"
    )

    def __repr__(self) -> str:
        return (
            f"<ReviewDecision id={self.id} task={self.review_task_id} "
            f"decision={self.decision} reviewer={self.reviewer_id}>"
        )
