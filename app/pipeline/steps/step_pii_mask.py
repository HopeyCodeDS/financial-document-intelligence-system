"""
Pipeline step: PII masking.

CRITICAL — pipeline halts if this step fails.
Text must NEVER reach the LLM without passing through this step.
"""
from __future__ import annotations

import json

from app.config import Settings
from app.core.exceptions import PIIMaskingError
from app.core.logging import get_logger
from app.models.pii_mapping import PIIMapping
from app.pipeline.context import PipelineContext
from app.pipeline.steps.base import AbstractPipelineStep
from app.services.pii.crypto import encrypt_mapping
from app.services.pii.masker import PIIMaskingService

logger = get_logger(__name__)


class StepPIIMask(AbstractPipelineStep):
    critical = True

    def __init__(
        self,
        masker: PIIMaskingService,
        settings: Settings,
        db_session: object,
    ) -> None:
        self._masker = masker
        self._settings = settings
        self._session = db_session

    @property
    def name(self) -> str:
        return "pii_mask"

    async def execute(self, context: PipelineContext) -> PipelineContext:
        if context.ocr_result is None:
            raise PIIMaskingError("OCR result is missing — cannot mask PII")

        full_text = context.ocr_result.full_text
        masking_result, reverse_map = self._masker.mask(full_text)

        # Validate no PII leaked through
        if not self._masker.validate_no_pii_leakage(masking_result.masked_text):
            raise PIIMaskingError(
                "PII leakage detected after masking — aborting pipeline"
            )

        context.masking_result = masking_result

        # Encrypt and persist the reverse mapping
        if reverse_map:
            encrypted = encrypt_mapping(
                json.dumps(reverse_map),
                self._settings.pii_encryption_key,
            )
            from sqlalchemy.ext.asyncio import AsyncSession
            session: AsyncSession = self._session  # type: ignore[assignment]

            pii_record = PIIMapping(
                document_id=context.document_id,
                encrypted_mapping=encrypted,
                entity_count=masking_result.entity_count,
            )
            session.add(pii_record)
            await session.flush()
            await session.refresh(pii_record)
            context.pii_mapping_id = pii_record.id

        logger.info(
            "pii_masking_step_complete",
            document_id=str(context.document_id),
            entity_count=masking_result.entity_count,
        )
        return context
