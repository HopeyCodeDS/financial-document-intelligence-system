"""
PipelineOrchestrator — sequences all pipeline steps and enforces security invariants.

Step execution order is HARDCODED and non-negotiable:
1. OCR          (critical) — extract text
2. PII Mask     (critical) — mask before LLM — MUST come before StepLLMExtract
3. LLM Extract  (non-critical)
4. Validate     (non-critical)
5. Risk Detect  (non-critical)
6. Audit        (critical) — always write audit trail

If a critical step fails, pipeline halts immediately.
If a non-critical step fails, the error is recorded and subsequent steps still run.
"""
from __future__ import annotations

import time
import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.exceptions import PipelineError
from app.core.logging import get_logger
from app.db.repositories.document import DocumentRepository
from app.models.document import DocumentStatus
from app.pipeline.context import PipelineContext
from app.pipeline.steps.base import AbstractPipelineStep
from app.pipeline.steps.step_llm_extract import StepLLMExtract
from app.pipeline.steps.step_ocr import StepOCR
from app.pipeline.steps.step_pii_mask import StepPIIMask
from app.pipeline.steps.step_risk import StepRisk
from app.pipeline.steps.step_validate import StepValidate
from app.services.llm.extractor import LLMExtractionService
from app.services.ocr.router import OCRRouter
from app.services.pii.masker import PIIMaskingService
from app.services.risk.detector import RiskDetectionService
from app.services.storage import LocalStorageService
from app.services.validation.engine import ValidationEngine

logger = get_logger(__name__)


class PipelineOrchestrator:
    """Assembles and runs the full document processing pipeline."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._doc_repo = DocumentRepository(session)

        # Build services
        storage = LocalStorageService(root=settings.storage_local_root)
        ocr_router = OCRRouter()
        masker = PIIMaskingService()
        llm_extractor = LLMExtractionService(settings)
        validation_engine = ValidationEngine()
        risk_detector = RiskDetectionService(settings)

        # Build ordered step list
        self._steps: list[AbstractPipelineStep] = [
            StepOCR(storage=storage, ocr_router=ocr_router),
            StepPIIMask(masker=masker, settings=settings, db_session=session),
            StepLLMExtract(extractor=llm_extractor, settings=settings, db_session=session),
            StepValidate(engine=validation_engine, db_session=session),
            StepRisk(detector=risk_detector, db_session=session),
        ]

    async def run(self, document_id: uuid.UUID) -> PipelineContext:
        """
        Execute the full pipeline for a document.

        Updates document status in DB at each stage.
        Always writes audit events regardless of success/failure.
        """
        # Load document to get type and file path
        document = await self._doc_repo.get_by_id(document_id)
        if document is None:
            raise PipelineError("orchestrator", f"Document {document_id} not found")

        context = PipelineContext(
            document_id=document_id,
            document_type=document.document_type,
            file_path=document.file_path,
        )

        structlog.contextvars.bind_contextvars(document_id=str(document_id))
        logger.info("pipeline_started", document_type=document.document_type.value)

        # Status transitions per step
        _step_status_map = {
            "ocr": DocumentStatus.ocr_complete,
            "pii_mask": DocumentStatus.masked,
            "llm_extract": DocumentStatus.extracted,
            "validate": DocumentStatus.validated,
            "risk_detect": DocumentStatus.validated,  # stays validated after risk
        }

        for step in self._steps:
            step_start = time.monotonic()
            try:
                context = await step.execute(context)
                duration_ms = (time.monotonic() - step_start) * 1000
                context.record_step_duration(step.name, duration_ms)

                # Update document status
                new_status = _step_status_map.get(step.name)
                if new_status:
                    await self._doc_repo.update_status(document_id, new_status)

                logger.info(
                    "pipeline_step_complete",
                    step=step.name,
                    duration_ms=round(duration_ms),
                )

            except Exception as exc:
                duration_ms = (time.monotonic() - step_start) * 1000
                context.add_error(step.name, str(exc))
                logger.exception(
                    "pipeline_step_failed",
                    step=step.name,
                    critical=step.critical,
                    error=str(exc),
                )

                if step.critical:
                    # Critical failure — mark document failed and halt
                    await self._doc_repo.update_status(
                        document_id,
                        DocumentStatus.failed,
                        error_message=f"Step '{step.name}' failed: {exc}",
                    )
                    context.final_status = DocumentStatus.failed.value
                    # Audit the failure before returning
                    await self._write_audit_event(context, step.name, "failure", str(exc))
                    raise PipelineError(step.name, str(exc)) from exc

        # Determine final status
        has_errors = any("failed" in e.lower() for e in context.errors)
        if has_errors or not context.extraction_result:
            context.final_status = DocumentStatus.failed.value
        else:
            context.final_status = DocumentStatus.validated.value

        await self._doc_repo.update_status(
            document_id,
            DocumentStatus(context.final_status),
        )

        await self._write_audit_event(context, "orchestrator", "success")

        logger.info(
            "pipeline_complete",
            final_status=context.final_status,
            total_ms=round(context.elapsed_ms),
        )
        return context

    async def _write_audit_event(
        self,
        context: PipelineContext,
        step_name: str,
        status: str,
        error: str | None = None,
    ) -> None:
        """Write a pipeline-level audit event."""
        from app.models.audit_log import AuditEventCategory, AuditEventStatus, AuditLog

        event = AuditLog(
            document_id=context.document_id,
            event_type=f"pipeline.{status}",
            event_category=AuditEventCategory.pipeline,
            actor=context.actor,
            step_name=step_name,
            duration_ms=int(context.elapsed_ms),
            status=AuditEventStatus.success if status == "success" else AuditEventStatus.failure,
            details={
                "step_timings": {k: round(v) for k, v in context.step_timings.items()},
                "errors": context.errors,
                "final_status": context.final_status,
                **({"error": error} if error else {}),
            },
        )
        self._session.add(event)
        try:
            await self._session.flush()
        except Exception as exc:
            # Audit write failure must be logged but must NOT mask the original error
            logger.exception("audit_write_failed", error=str(exc))
