"""Pipeline step: validation engine."""
from __future__ import annotations


from app.core.logging import get_logger
from app.models.extraction import ValidationStatus
from app.pipeline.context import PipelineContext
from app.pipeline.steps.base import AbstractPipelineStep
from app.services.validation.engine import ValidationEngine

logger = get_logger(__name__)


class StepValidate(AbstractPipelineStep):
    critical = False

    def __init__(self, engine: ValidationEngine, db_session: object) -> None:
        self._engine = engine
        self._session = db_session

    @property
    def name(self) -> str:
        return "validate"

    async def execute(self, context: PipelineContext) -> PipelineContext:
        if context.extraction_result is None or context.extraction_db_id is None:
            context.add_error(self.name, "No extraction result — skipping validation")
            return context

        result = self._engine.run(context.extraction_result, context.document_type)
        context.validation_result = result

        # Update the ExtractionResult DB record
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.models.extraction import ExtractionResult

        session: AsyncSession = self._session  # type: ignore[assignment]
        db_record = await session.get(ExtractionResult, context.extraction_db_id)
        if db_record:
            db_record.validation_status = (
                ValidationStatus.passed if result.passed else ValidationStatus.failed
            )
            db_record.validation_violations = [
                v.model_dump() for v in result.violations
            ]
            await session.flush()

        return context
