"""
python-doctr neural OCR service.

Best for complex financial document layouts (multi-column, mixed tables/text).
Uses the doctr library which provides a deep-learning OCR pipeline.
"""
from __future__ import annotations

import asyncio


from app.core.exceptions import OCRError, OCRPageExtractionError
from app.core.logging import get_logger
from app.schemas.ocr import BoundingBox, OCRResult, PageOCRResult, TextBlock
from app.services.ocr.base import AbstractOCRService

logger = get_logger(__name__)


class DoctrService(AbstractOCRService):
    """Neural OCR via python-doctr for complex document layouts."""

    def __init__(self) -> None:
        self._model: object | None = None

    def _get_model(self) -> object:
        """Lazily load the doctr model (heavy import — only on first use)."""
        if self._model is None:
            try:
                from doctr.models import ocr_predictor
                self._model = ocr_predictor(pretrained=True)
                logger.info("doctr_model_loaded")
            except ImportError as exc:
                raise OCRError(f"python-doctr not installed: {exc}") from exc
        return self._model

    def can_handle(self, file_bytes: bytes) -> bool:
        """doctr can handle any PDF — position it between pdfplumber and tesseract."""
        return True

    async def extract(self, file_bytes: bytes, document_id: str) -> OCRResult:
        loop = asyncio.get_event_loop()
        pages = await loop.run_in_executor(None, self._extract_sync, file_bytes, document_id)
        logger.info(
            "doctr_extraction_complete",
            document_id=document_id,
            page_count=len(pages),
        )
        return OCRResult.from_pages(document_id, pages, strategy="doctr")

    def _extract_sync(self, file_bytes: bytes, document_id: str) -> list[PageOCRResult]:
        try:
            from doctr.io import DocumentFile
        except ImportError as exc:
            raise OCRError(f"doctr dependencies not installed: {exc}") from exc

        model = self._get_model()

        try:
            doc = DocumentFile.from_pdf(file_bytes)
            result = model(doc)  # type: ignore[operator]
        except Exception as exc:
            raise OCRError(f"doctr extraction failed: {exc}") from exc

        pages = []
        for page_idx, page in enumerate(result.pages):
            try:
                page_result = self._convert_page(page, page_idx + 1)
                pages.append(page_result)
            except Exception as exc:
                raise OCRPageExtractionError(page_idx + 1, str(exc)) from exc

        return pages

    @staticmethod
    def _convert_page(page: object, page_number: int) -> PageOCRResult:
        """Convert a doctr Page object to our PageOCRResult schema."""
        blocks: list[TextBlock] = []
        lines_text: list[str] = []

        for block in page.blocks:  # type: ignore[attr-defined]
            for line in block.lines:
                words = [word.value for word in line.words]
                if not words:
                    continue
                line_text = " ".join(words)
                lines_text.append(line_text)

                # doctr geometry is [[x0,y0],[x1,y1]] normalised [0,1]
                geo = line.geometry
                blocks.append(
                    TextBlock(
                        text=line_text,
                        bbox=BoundingBox(
                            x0=float(geo[0][0]),
                            y0=float(geo[0][1]),
                            x1=float(geo[1][0]),
                            y1=float(geo[1][1]),
                        ),
                        block_type="text",
                    )
                )

        raw_text = "\n".join(lines_text)
        return PageOCRResult(
            page_number=page_number,
            raw_text=raw_text,
            blocks=blocks,
        )
