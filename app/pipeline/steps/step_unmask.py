"""
Pipeline step: PII unmasking.

Runs AFTER ``StepLLMExtract`` and BEFORE ``StepValidate``. Decrypts the
per-document reverse mapping persisted by ``StepPIIMask`` and substitutes
mask tokens (``[PERSON_1]``, ``[IBAN_2]`` …) back to real values in the
extracted structured payload — so validation rules, risk detection, and
the analyst-facing record all see real data.

Non-critical by design: a decryption or re-validation failure leaves the
masked data in place (the safer failure mode for a compliance system) and
records a pipeline error rather than halting the run. The encrypted
``pii_mappings`` row remains the audit bridge between the masked LLM input
and the unmasked record.
"""
from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.exceptions import PIIDecryptionError
from app.core.logging import get_logger
from app.models.extraction import ExtractionResult
from app.models.pii_mapping import PIIMapping
from app.pipeline.context import PipelineContext
from app.pipeline.steps.base import AbstractPipelineStep
from app.services.llm.output_parser import SCHEMA_MAP
from app.services.pii.crypto import decrypt_mapping
from app.services.pii.unmasker import unmask_structured

logger = get_logger(__name__)


class StepUnmask(AbstractPipelineStep):
    critical = False

    def __init__(self, settings: Settings, db_session: AsyncSession) -> None:
        self._settings = settings
        self._session = db_session

    @property
    def name(self) -> str:
        return "unmask"

    async def execute(self, context: PipelineContext) -> PipelineContext:
        if context.extraction_result is None:
            context.add_error(self.name, "Extraction result missing — skipping unmask")
            return context

        if context.pii_mapping_id is None:
            logger.info(
                "unmask_skipped_no_pii",
                document_id=str(context.document_id),
            )
            return context

        mapping_row = await self._session.get(PIIMapping, context.pii_mapping_id)
        if mapping_row is None:
            context.add_error(
                self.name,
                f"PIIMapping {context.pii_mapping_id} not found",
            )
            return context

        try:
            plaintext = decrypt_mapping(
                mapping_row.encrypted_mapping,
                self._settings.pii_encryption_key,
            )
            reverse_map: dict[str, str] = json.loads(plaintext)
        except (PIIDecryptionError, json.JSONDecodeError) as exc:
            logger.exception(
                "unmask_decrypt_failed",
                document_id=str(context.document_id),
                error=str(exc),
            )
            context.add_error(self.name, f"Failed to decrypt PII mapping: {exc}")
            return context

        schema_class = SCHEMA_MAP.get(context.document_type)
        if schema_class is None:
            context.add_error(
                self.name,
                f"No extraction schema for document type {context.document_type.value}",
            )
            return context

        masked_dump = context.extraction_result.model_dump()
        unmasked_dump = unmask_structured(masked_dump, reverse_map)

        try:
            unmasked_model = schema_class.model_validate(unmasked_dump)
        except Exception as exc:
            logger.exception(
                "unmask_revalidate_failed",
                document_id=str(context.document_id),
                error=str(exc),
            )
            context.add_error(
                self.name, f"Unmasked payload failed schema re-validation: {exc}"
            )
            return context

        context.extraction_result = unmasked_model

        if context.extraction_db_id is not None:
            extraction_row = await self._session.get(
                ExtractionResult, context.extraction_db_id
            )
            if extraction_row is None:
                context.add_error(
                    self.name,
                    f"ExtractionResult {context.extraction_db_id} not found",
                )
                return context
            extraction_row.structured_data = unmasked_model.model_dump()
            await self._session.flush()

        logger.info(
            "unmask_step_complete",
            document_id=str(context.document_id),
            tokens_replaced=len(reverse_map),
        )
        return context
