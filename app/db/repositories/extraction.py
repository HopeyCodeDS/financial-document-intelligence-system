"""
ExtractionResult repository.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.base import BaseRepository
from app.models.extraction import ExtractionResult


class ExtractionResultRepository(BaseRepository[ExtractionResult]):
    model = ExtractionResult

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_document_id(self, document_id: uuid.UUID) -> ExtractionResult | None:
        result = await self._session.execute(
            select(ExtractionResult)
            .where(ExtractionResult.document_id == document_id)
            .order_by(ExtractionResult.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
