"""
ExtractionResult ORM model — stores structured data extracted by the LLM.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ValidationStatus(str, enum.Enum):
    passed = "passed"
    failed = "failed"
    partial = "partial"


class RiskLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ExtractionResult(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "extraction_results"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Model provenance
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    extracted_at: Mapped[str] = mapped_column(String(32), nullable=False)  # ISO datetime

    # LLM output — stored encrypted at application layer before persisting
    raw_llm_response_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Validated extraction (JSON)
    structured_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    confidence_scores: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    overall_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Validation
    validation_status: Mapped[ValidationStatus] = mapped_column(
        Enum(ValidationStatus, name="validation_status_enum"),
        nullable=False,
        default=ValidationStatus.passed,
    )
    validation_violations: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )

    # Risk
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="risk_level_enum"),
        nullable=False,
        default=RiskLevel.low,
    )
    risk_flags: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )

    # Relationships
    document: Mapped["Document"] = relationship(  # noqa: F821
        "Document", back_populates="extraction_results"
    )
    review_tasks: Mapped[list] = relationship(
        "ReviewTask", back_populates="extraction_result"
    )

    def __repr__(self) -> str:
        return (
            f"<ExtractionResult id={self.id} doc={self.document_id} "
            f"risk={self.risk_level} confidence={self.overall_confidence:.2f}>"
        )
