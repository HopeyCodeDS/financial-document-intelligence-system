"""
Document repository — data access layer for the documents table.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.base import BaseRepository
from app.models.document import Document, DocumentStatus, DocumentType


class DocumentRepository(BaseRepository[Document]):
    model = Document

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        return await self._session.get(Document, document_id)

    async def list_filtered(
        self,
        document_type: DocumentType | None = None,
        status: DocumentStatus | None = None,
        uploaded_by: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Document], int]:
        from sqlalchemy import func

        query = select(Document)
        count_query = select(func.count()).select_from(Document)

        if document_type is not None:
            query = query.where(Document.document_type == document_type)
            count_query = count_query.where(Document.document_type == document_type)
        if status is not None:
            query = query.where(Document.status == status)
            count_query = count_query.where(Document.status == status)
        if uploaded_by is not None:
            query = query.where(Document.uploaded_by == uploaded_by)
            count_query = count_query.where(Document.uploaded_by == uploaded_by)

        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        result = await self._session.execute(
            query.order_by(Document.created_at.desc()).offset(offset).limit(limit)
        )
        items = list(result.scalars().all())
        return items, total

    async def update_status(
        self,
        document_id: uuid.UUID,
        status: DocumentStatus,
        error_message: str | None = None,
    ) -> Document | None:
        doc = await self.get_by_id(document_id)
        if doc is None:
            return None
        doc.status = status
        if error_message is not None:
            doc.error_message = error_message
        await self._session.flush()
        await self._session.refresh(doc)
        return doc

    async def update_page_count(
        self,
        document_id: uuid.UUID,
        page_count: int,
    ) -> Document | None:
        doc = await self.get_by_id(document_id)
        if doc is None:
            return None
        doc.page_count = page_count
        await self._session.flush()
        return doc
