"""
Generic async repository base class.

Provides standard CRUD operations over an SQLAlchemy async session.
Subclasses only need to override where behaviour differs.
"""
from __future__ import annotations

import uuid
from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, record_id: uuid.UUID) -> ModelT | None:
        result = await self._session.get(self.model, record_id)
        return result

    async def list(
        self,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ModelT], int]:
        count_result = await self._session.execute(
            select(func.count()).select_from(self.model)
        )
        total = count_result.scalar_one()

        result = await self._session.execute(
            select(self.model).offset(offset).limit(limit)
        )
        items = list(result.scalars().all())
        return items, total

    async def save(self, instance: ModelT) -> ModelT:
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        await self._session.delete(instance)
        await self._session.flush()
