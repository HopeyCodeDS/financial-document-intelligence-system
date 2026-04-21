"""Pipeline step: risk detection."""
from __future__ import annotations

from app.core.logging import get_logger
from app.pipeline.context import PipelineContext
from app.pipeline.steps.base import AbstractPipelineStep
from app.services.risk.detector import RiskDetectionService

logger = get_logger(__name__)


class StepRisk(AbstractPipelineStep):
    critical = False

    def __init__(self, detector: RiskDetectionService, db_session: object) -> None:
        self._detector = detector
        self._session = db_session

    @property
    def name(self) -> str:
        return "risk_detect"

    async def execute(self, context: PipelineContext) -> PipelineContext:
        if context.extraction_result is None or context.extraction_db_id is None:
            context.add_error(self.name, "No extraction result — skipping risk detection")
            return context

        assessment = self._detector.detect(
            context.extraction_result, context.document_type
        )
        context.risk_assessment = assessment

        # Update ExtractionResult with risk data
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.models.extraction import ExtractionResult

        session: AsyncSession = self._session  # type: ignore[assignment]
        db_record = await session.get(ExtractionResult, context.extraction_db_id)
        if db_record:
            db_record.risk_level = assessment.risk_level
            db_record.risk_flags = [f.model_dump() for f in assessment.flags]
            await session.flush()

        # Auto-create ReviewTask if risk requires it
        if assessment.requires_review and context.extraction_db_id:
            await self._create_review_task(context, assessment)

        return context

    async def _create_review_task(self, context: PipelineContext, assessment: object) -> None:
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.models.review import ReviewPriority, ReviewTask, ReviewTaskStatus
        from app.models.extraction import RiskLevel

        session: AsyncSession = self._session  # type: ignore[assignment]

        risk_to_priority = {
            RiskLevel.medium: ReviewPriority.medium,
            RiskLevel.high: ReviewPriority.high,
            RiskLevel.critical: ReviewPriority.urgent,
        }
        priority = risk_to_priority.get(
            assessment.risk_level,  # type: ignore[attr-defined]
            ReviewPriority.medium,
        )

        review_task = ReviewTask(
            document_id=context.document_id,
            extraction_result_id=context.extraction_db_id,
            priority=priority,
            trigger_reason=assessment.summary,  # type: ignore[attr-defined]
            status=ReviewTaskStatus.pending,
        )
        session.add(review_task)
        await session.flush()

        logger.info(
            "review_task_created",
            document_id=str(context.document_id),
            priority=priority.value,
            risk_level=assessment.risk_level.value,  # type: ignore[attr-defined]
        )
