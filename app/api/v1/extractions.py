"""
Extraction result endpoints.

GET /api/v1/extractions/{document_id} — get the extraction result for a document
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DocumentNotFoundError
from app.db.repositories.extraction import ExtractionResultRepository
from app.db.session import get_db_session
from app.dependencies import get_current_user
from app.schemas.extraction_response import ExtractionResultResponse

router = APIRouter(prefix="/extractions", tags=["Extractions"])


@router.get(
    "/{document_id}",
    response_model=ExtractionResultResponse,
    summary="Get extraction result for a document",
)
async def get_extraction_result(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(get_current_user),
) -> ExtractionResultResponse:
    repo = ExtractionResultRepository(db)
    result = await repo.get_by_document_id(document_id)
    if result is None:
        raise DocumentNotFoundError(str(document_id))
    return ExtractionResultResponse.model_validate(result)
