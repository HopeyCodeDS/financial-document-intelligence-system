"""
Pydantic schemas for the Document domain.

These are the API I/O contracts — distinct from the ORM models.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.document import DocumentStatus, DocumentType


class DocumentUploadResponse(BaseModel):
    """Returned immediately after a successful upload (HTTP 202)."""

    document_id: uuid.UUID
    status: DocumentStatus
    message: str = "Document accepted for processing"
    task_id: str | None = None


class DocumentStatusResponse(BaseModel):
    """Current processing state of a document."""

    document_id: uuid.UUID
    filename: str
    document_type: DocumentType
    status: DocumentStatus
    page_count: int | None
    file_size_bytes: int
    uploaded_by: str
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""

    items: list[DocumentStatusResponse]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)

    @property
    def has_more(self) -> bool:
        return self.page * self.page_size < self.total


class DocumentTypeQuery(BaseModel):
    """Query parameters for filtering documents."""

    document_type: DocumentType | None = None
    status: DocumentStatus | None = None
    uploaded_by: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
