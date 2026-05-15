"""
API response schema for extraction results.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.extraction import RiskLevel, ValidationStatus


class BoundingBox(BaseModel):
    """Source-document coordinates for a single extracted field.

    Currently optional and unpopulated — the OCR layer will start emitting
    these in a follow-up. The shape is fixed now so the UI can render
    overlays as soon as values arrive without an API contract change.

    Coordinates are normalised to ``[0, 1]`` against the page dimensions so
    they're resolution-independent on the client. ``page`` is 1-indexed.
    """

    page: int = Field(ge=1)
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    width: float = Field(gt=0.0, le=1.0)
    height: float = Field(gt=0.0, le=1.0)


class ExtractionResultResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    document_type: str
    model_version: str
    extracted_at: str
    structured_data: dict[str, Any]
    confidence_scores: dict[str, float]
    overall_confidence: float
    validation_status: ValidationStatus
    validation_violations: list[dict[str, Any]]
    risk_level: RiskLevel
    risk_flags: list[dict[str, Any]]
    # Optional: per-field source coordinates. Keyed by the same field name
    # used in `confidence_scores`. May be missing or empty until the OCR
    # layer starts reporting them.
    bounding_boxes: dict[str, list[BoundingBox]] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
