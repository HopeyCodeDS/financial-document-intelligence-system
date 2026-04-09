"""
Pipeline step: LLM extraction.

Runs AFTER PII masking. Uses only masked text.
"""
from __future__ import annotations

from datetime import UTC, datetime

from app.config import Settings
from app.core.logging import get_logger
from app.models.extraction import ExtractionResult, RiskLevel, ValidationStatus
from app.pipeline.context import PipelineContext
from app.pipeline.steps.base import AbstractPipelineStep
from app.services.llm.extractor import LLMExtractionService
from app.services.pii.crypto import encrypt_mapping

logger = get_logger(__name__)


class StepLLMExtract(AbstractPipelineStep):
    critical = False

    def __init__(self, extractor: LLMExtractionService, settings: Settings, db_session: object) -> None:
        self._extractor = extractor
        self._settings = settings
        self._session = db_session

    @property
    def name(self) -> str:
        return "llm_extract"

    async def execute(self, context: PipelineContext) -> PipelineContext:
        if context.masking_result is None:
            context.add_error(self.name, "Masking result missing — skipping LLM extraction")
            return context

        masked_text = context.masking_result.masked_text

        extraction, confidence_scores, overall_confidence, raw_response = (
            await self._extractor.extract(
                masked_text=masked_text,
                document_type=context.document_type,
                document_id=str(context.document_id),
            )
        )

        context.extraction_result = extraction

        # Encrypt raw LLM response before persisting
        encrypted_response = encrypt_mapping(raw_response, self._settings.pii_encryption_key)

        # Persist extraction result
        from sqlalchemy.ext.asyncio import AsyncSession
        session: AsyncSession = self._session  # type: ignore[assignment]

        db_record = ExtractionResult(
            document_id=context.document_id,
            document_type=context.document_type.value,
            model_version=self._extractor.model_version,
            extracted_at=datetime.now(UTC).isoformat(),
            raw_llm_response_encrypted=encrypted_response,
            structured_data=extraction.model_dump(),
            confidence_scores=confidence_scores,
            overall_confidence=overall_confidence,
            validation_status=ValidationStatus.passed,  # updated by validation step
            risk_level=RiskLevel.low,  # updated by risk step
        )
        session.add(db_record)
        await session.flush()
        await session.refresh(db_record)
        context.extraction_db_id = db_record.id

        return context
