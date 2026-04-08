"""
Document ORM model — represents an uploaded financial document.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, String, Text, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class DocumentType(str, enum.Enum):
    bank_statement = "bank_statement"
    invoice = "invoice"
    portfolio = "portfolio"


class DocumentStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    ocr_complete = "ocr_complete"
    masked = "masked"
    extracted = "extracted"
    validated = "validated"
    reviewed = "reviewed"
    failed = "failed"


class Document(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "documents"

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="document_type_enum"), nullable=False
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status_enum"),
        nullable=False,
        default=DocumentStatus.uploaded,
        server_default="uploaded",
    )

    # Storage — UUID-based path, never the original filename on disk
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 hex
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Actor
    uploaded_by: Mapped[str] = mapped_column(String(255), nullable=False)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Extensible metadata (document source, client ref, etc.)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )

    # Relationships
    extraction_results: Mapped[list] = relationship(
        "ExtractionResult", back_populates="document", cascade="all, delete-orphan"
    )
    pii_mappings: Mapped[list] = relationship(
        "PIIMapping", back_populates="document", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list] = relationship(
        "AuditLog", back_populates="document"
    )
    review_tasks: Mapped[list] = relationship(
        "ReviewTask", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} type={self.document_type} status={self.status}>"
