"""
Document API endpoints.

POST /api/v1/documents/upload  — upload a PDF, returns 202 with job ID
GET  /api/v1/documents/{id}    — get document status
GET  /api/v1/documents/        — list documents (paginated)
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.exceptions import (
    DocumentNotFoundError,
    FileTooLargeError,
    InvalidFileTypeError,
)
from app.db.repositories.document import DocumentRepository
from app.db.session import get_db_session
from app.dependencies import CurrentUser, get_app_settings
from app.models.document import Document, DocumentStatus, DocumentType
from app.schemas.document import (
    DocumentListResponse,
    DocumentStatusResponse,
    DocumentUploadResponse,
)
from app.services.storage import LocalStorageService

router = APIRouter(prefix="/documents", tags=["Documents"])

ALLOWED_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}


@router.post(
    "/upload",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DocumentUploadResponse,
    summary="Upload a financial document for processing",
)
async def upload_document(
    file: Annotated[UploadFile, File(description="PDF file to process")],
    document_type: Annotated[
        DocumentType, Form(description="Type of financial document")
    ],
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    current_user: str = Depends(CurrentUser),  # type: ignore[misc]
) -> DocumentUploadResponse:
    """
    Accept a PDF document and enqueue it for processing.

    Returns HTTP 202 immediately with a document_id and task_id.
    Poll GET /documents/{id} for processing status.
    """
    # Validate content type
    content_type = file.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES and not file.filename.endswith(".pdf"):
        raise InvalidFileTypeError(content_type)

    # Read and validate file size
    content = await file.read()
    if len(content) > settings.storage_max_file_size_bytes:
        raise FileTooLargeError(len(content), settings.storage_max_file_size_bytes)

    # Persist to storage
    doc_id = uuid.uuid4()
    storage = LocalStorageService(root=settings.storage_local_root)
    file_path = await storage.save(doc_id, content)
    file_hash = storage.compute_sha256(content)

    # Create DB record
    repo = DocumentRepository(db)
    document = Document(
        id=doc_id,
        filename=file.filename or f"{doc_id}.pdf",
        document_type=document_type,
        status=DocumentStatus.uploaded,
        file_path=file_path,
        file_hash=file_hash,
        file_size_bytes=len(content),
        uploaded_by=current_user,
    )
    await repo.save(document)

    # Enqueue processing task
    from app.tasks.document_tasks import process_document
    task = process_document.delay(str(doc_id))

    # Update status to processing
    await repo.update_status(doc_id, DocumentStatus.processing)

    return DocumentUploadResponse(
        document_id=doc_id,
        status=DocumentStatus.processing,
        task_id=task.id,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentStatusResponse,
    summary="Get document processing status",
)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(CurrentUser),  # type: ignore[misc]
) -> DocumentStatusResponse:
    repo = DocumentRepository(db)
    document = await repo.get_by_id(document_id)
    if document is None:
        raise DocumentNotFoundError(str(document_id))
    return DocumentStatusResponse.model_validate(document)


@router.get(
    "/",
    response_model=DocumentListResponse,
    summary="List documents",
)
async def list_documents(
    document_type: DocumentType | None = Query(default=None),
    status_filter: DocumentStatus | None = Query(default=None, alias="status"),
    uploaded_by: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(CurrentUser),  # type: ignore[misc]
) -> DocumentListResponse:
    repo = DocumentRepository(db)
    offset = (page - 1) * page_size
    items, total = await repo.list_filtered(
        document_type=document_type,
        status=status_filter,
        uploaded_by=uploaded_by,
        offset=offset,
        limit=page_size,
    )
    return DocumentListResponse(
        items=[DocumentStatusResponse.model_validate(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
    )
