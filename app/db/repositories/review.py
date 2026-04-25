"""
Review task and decision repositories.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.base import BaseRepository
from app.models.review import ReviewDecision, ReviewTask, ReviewTaskStatus


class ReviewTaskRepository(BaseRepository[ReviewTask]):
    model = ReviewTask

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_pending(
        self,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ReviewTask], int]:
        from sqlalchemy import func

        q = select(ReviewTask).where(
            ReviewTask.status.in_([ReviewTaskStatus.pending, ReviewTaskStatus.in_review])
        ).order_by(ReviewTask.created_at.asc())

        count_q = select(func.count()).select_from(ReviewTask).where(
            ReviewTask.status.in_([ReviewTaskStatus.pending, ReviewTaskStatus.in_review])
        )

        total = (await self._session.execute(count_q)).scalar_one()
        items = list((await self._session.execute(q.offset(offset).limit(limit))).scalars().all())
        return items, total

    async def update_status(
        self, task_id: uuid.UUID, status: ReviewTaskStatus
    ) -> ReviewTask | None:
        task = await self.get_by_id(task_id)
        if task is None:
            return None
        task.status = status
        await self._session.flush()
        return task

    async def get_for_update(self, task_id: uuid.UUID) -> ReviewTask | None:
        """Fetch a review task with a row-level lock (SELECT ... FOR UPDATE).

        Use this from any flow that reads-then-writes the task to prevent two
        concurrent reviewers from both seeing status='pending' and each
        creating a decision. The lock is released when the surrounding
        transaction commits or rolls back.
        """
        query = (
            select(ReviewTask)
            .where(ReviewTask.id == task_id)
            .with_for_update()
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()


class ReviewDecisionRepository(BaseRepository[ReviewDecision]):
    model = ReviewDecision

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
