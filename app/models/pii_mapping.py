"""
PIIMapping ORM model — encrypted reverse mapping of PII tokens to original values.

Stored per document. The encrypted_mapping column contains an AES-256-GCM ciphertext
that decrypts to a JSON dict: { "[PERSON_1]": "John Smith", "[IBAN_1]": "CH56..." }.

Decryption is only performed at human review stage, never during pipeline processing.
"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import UTC, datetime
from sqlalchemy import DateTime, func

from app.models.base import Base, UUIDMixin


class PIIMapping(Base, UUIDMixin):
    __tablename__ = "pii_mappings"
    __table_args__ = (
        UniqueConstraint("document_id", name="uq_pii_mapping_document"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # AES-256-GCM encrypted JSON: {"[PERSON_1]": "...", "[IBAN_1]": "..."}
    # Format: base64(nonce || ciphertext || tag)
    encrypted_mapping: Mapped[str] = mapped_column(Text, nullable=False)

    # Number of PII entities masked (for audit purposes — not the values themselves)
    entity_count: Mapped[int] = mapped_column(nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    document: Mapped["Document"] = relationship(  # noqa: F821
        "Document", back_populates="pii_mappings"
    )

    def __repr__(self) -> str:
        return (
            f"<PIIMapping id={self.id} doc={self.document_id} entities={self.entity_count}>"
        )
