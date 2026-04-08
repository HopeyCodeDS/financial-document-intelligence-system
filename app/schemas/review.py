"""
Pydantic schemas for the human review interface.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.review import (
    ReviewDecisionType,
    ReviewPriority,
    ReviewTaskStatus,
)


class ReviewTaskResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    extraction_result_id: uuid.UUID
    priority: ReviewPriority
    trigger_reason: str
    status: ReviewTaskStatus
    assigned_to: str | None
    due_by: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReviewTaskListResponse(BaseModel):
    items: list[ReviewTaskResponse]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class SubmitReviewDecisionRequest(BaseModel):
    """Reviewer submits a decision on a review task."""

    decision: ReviewDecisionType
    confidence_override: float | None = Field(default=None, ge=0.0, le=1.0)
    notes: str | None = None
    corrections: dict[str, Any] | None = None  # {field: {original, corrected}}


class ReviewDecisionResponse(BaseModel):
    id: uuid.UUID
    review_task_id: uuid.UUID
    reviewer_id: str
    decided_at: datetime
    decision: ReviewDecisionType
    confidence_override: float | None
    notes: str | None
    corrections: dict[str, Any] | None

    model_config = {"from_attributes": True}
