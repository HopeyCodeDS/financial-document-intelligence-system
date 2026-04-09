"""Pipeline step: OCR extraction."""
from __future__ import annotations

from app.core.logging import get_logger
from app.pipeline.context import PipelineContext
from app.pipeline.steps.base import AbstractPipelineStep
from app.services.ocr.router import OCRRouter
from app.services.storage import LocalStorageService

logger = get_logger(__name__)


class StepOCR(AbstractPipelineStep):
    critical = True

    def __init__(self, storage: LocalStorageService, ocr_router: OCRRouter) -> None:
        self._storage = storage
        self._ocr = ocr_router

    @property
    def name(self) -> str:
        return "ocr"

    async def execute(self, context: PipelineContext) -> PipelineContext:
        # Load file bytes
        context.file_bytes = await self._storage.load(context.file_path)

        # Run OCR strategy
        context.ocr_result = await self._ocr.extract(
            context.file_bytes,
            str(context.document_id),
        )
        return context
