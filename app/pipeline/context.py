"""
PipelineContext — shared state passed through all pipeline steps.

Each step reads only what it needs from previous steps and writes only to its
designated slot. Steps are decoupled from each other via this context object.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.models.document import DocumentStatus, DocumentType
from app.schemas.extraction import ExtractionPayload
from app.schemas.ocr import OCRResult
from app.schemas.pii import MaskingResult
from app.schemas.risk import RiskAssessment
from app.schemas.validation import ValidationResult


@dataclass
class PipelineContext:
    # Inputs (set before pipeline starts)
    document_id: uuid.UUID
    document_type: DocumentType
    file_path: str
    actor: str = "system"

    # Step outputs (populated as pipeline progresses)
    file_bytes: bytes | None = None
    ocr_result: OCRResult | None = None
    masking_result: MaskingResult | None = None
    pii_mapping_id: uuid.UUID | None = None
    extraction_result: ExtractionPayload | None = None
    extraction_db_id: uuid.UUID | None = None
    validation_result: ValidationResult | None = None
    risk_assessment: RiskAssessment | None = None

    # Pipeline metadata
    pipeline_start: datetime = field(default_factory=lambda: datetime.now(UTC))
    step_timings: dict[str, float] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    final_status: str = DocumentStatus.processing.value

    def add_error(self, step_name: str, message: str) -> None:
        self.errors.append(f"[{step_name}] {message}")

    def record_step_duration(self, step_name: str, duration_ms: float) -> None:
        self.step_timings[step_name] = duration_ms

    @property
    def elapsed_ms(self) -> float:
        return (datetime.now(UTC) - self.pipeline_start).total_seconds() * 1000
