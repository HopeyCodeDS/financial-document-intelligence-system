"""
API response schema for extraction results.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.extraction import RiskLevel, ValidationStatus


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
    created_at: datetime

    model_config = {"from_attributes": True}
