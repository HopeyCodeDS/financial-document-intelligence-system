"""
Human review API endpoints.

GET  /api/v1/review/              — list pending review tasks
GET  /api/v1/review/{task_id}     — get a specific task
POST /api/v1/review/{task_id}/decide — submit a review decision
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ReviewAlreadyDecidedError, ReviewTaskNotFoundError
from app.db.repositories.review import ReviewDecisionRepository, ReviewTaskRepository
from app.db.session import get_db_session
from app.dependencies import CurrentUser
from app.models.audit_log import AuditEventCategory, AuditEventStatus
from app.models.review import ReviewDecision, ReviewTaskStatus
from app.schemas.review import (
    ReviewDecisionResponse,
    ReviewTaskListResponse,
    ReviewTaskResponse,
    SubmitReviewDecisionRequest,
)
from app.services.audit.logger import AuditLogger

router = APIRouter(prefix="/review", tags=["Review"])

_TERMINAL_STATUSES = {
    ReviewTaskStatus.approved,
    ReviewTaskStatus.rejected,
    ReviewTaskStatus.escalated,
}


@router.get("/", response_model=ReviewTaskListResponse, summary="List pending review tasks")
async def list_review_queue(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(CurrentUser),  # type: ignore[misc]
) -> ReviewTaskListResponse:
    repo = ReviewTaskRepository(db)
    offset = (page - 1) * page_size
    items, total = await repo.list_pending(offset=offset, limit=page_size)
    return ReviewTaskListResponse(
        items=[ReviewTaskResponse.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{task_id}", response_model=ReviewTaskResponse, summary="Get review task")
async def get_review_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(CurrentUser),  # type: ignore[misc]
) -> ReviewTaskResponse:
    repo = ReviewTaskRepository(db)
    task = await repo.get_by_id(task_id)
    if task is None:
        raise ReviewTaskNotFoundError(str(task_id))
    return ReviewTaskResponse.model_validate(task)


@router.post(
    "/{task_id}/decide",
    response_model=ReviewDecisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a review decision",
)
async def submit_review_decision(
    task_id: uuid.UUID,
    body: SubmitReviewDecisionRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(CurrentUser),  # type: ignore[misc]
) -> ReviewDecisionResponse:
    task_repo = ReviewTaskRepository(db)
    decision_repo = ReviewDecisionRepository(db)
    audit = AuditLogger(db)

    task = await task_repo.get_by_id(task_id)
    if task is None:
        raise ReviewTaskNotFoundError(str(task_id))

    if task.status in _TERMINAL_STATUSES:
        raise ReviewAlreadyDecidedError(str(task_id), task.status.value)

    # Map decision to final task status
    decision_to_status = {
        "approved": ReviewTaskStatus.approved,
        "rejected": ReviewTaskStatus.rejected,
        "escalated": ReviewTaskStatus.escalated,
        "needs_correction": ReviewTaskStatus.in_review,
    }
    new_status = decision_to_status.get(body.decision.value, ReviewTaskStatus.in_review)

    # Create decision record
    decision = ReviewDecision(
        review_task_id=task_id,
        reviewer_id=current_user,
        decision=body.decision,
        confidence_override=body.confidence_override,
        notes=body.notes,
        corrections=body.corrections,
    )
    decision_repo._session.add(decision)

    # Update task status
    await task_repo.update_status(task_id, new_status)

    await db.flush()
    await db.refresh(decision)

    # Audit the review decision
    await audit.log_api_event(
        event_type=f"review.decision.{body.decision.value}",
        actor=current_user,
        status=AuditEventStatus.success,
        document_id=task.document_id,
        details={
            "task_id": str(task_id),
            "decision": body.decision.value,
            "has_corrections": bool(body.corrections),
            "has_confidence_override": body.confidence_override is not None,
        },
    )

    return ReviewDecisionResponse.model_validate(decision)
