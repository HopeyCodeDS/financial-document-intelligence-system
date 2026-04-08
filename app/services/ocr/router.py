"""
OCR strategy router — selects the best extraction strategy for a given PDF.

Strategy selection order:
1. PDFPlumber  — for PDFs with embedded text (fastest, most accurate)
2. DocTR       — for complex layouts where pdfplumber finds little text
3. Tesseract   — last resort for pure image/scanned PDFs

This is NOT an HTTP router.
"""
from __future__ import annotations

from app.core.exceptions import OCRError
from app.core.logging import get_logger
from app.schemas.ocr import OCRResult
from app.services.ocr.base import AbstractOCRService
from app.services.ocr.doctr_service import DoctrService
from app.services.ocr.pdfplumber_service import PDFPlumberService
from app.services.ocr.tesseract_service import TesseractService

logger = get_logger(__name__)


class OCRRouter:
    """Selects and executes the appropriate OCR strategy for a document."""

    def __init__(self) -> None:
        self._pdfplumber = PDFPlumberService()
        self._doctr = DoctrService()
        self._tesseract = TesseractService()

    async def extract(self, file_bytes: bytes, document_id: str) -> OCRResult:
        """
        Auto-select the best OCR strategy and extract text.

        Tries strategies in priority order. Logs which strategy was selected.
        Raises OCRError if all strategies fail.
        """
        strategies: list[tuple[str, AbstractOCRService]] = [
            ("pdfplumber", self._pdfplumber),
            ("doctr", self._doctr),
            ("tesseract", self._tesseract),
        ]

        for name, strategy in strategies:
            if strategy.can_handle(file_bytes):
                logger.info(
                    "ocr_strategy_selected",
                    strategy=name,
                    document_id=document_id,
                )
                try:
                    result = await strategy.extract(file_bytes, document_id)
                    if result.full_text.strip():
                        return result
                    logger.warning(
                        "ocr_strategy_empty_result",
                        strategy=name,
                        document_id=document_id,
                    )
                    # Try next strategy if result is empty
                except OCRError as exc:
                    logger.warning(
                        "ocr_strategy_failed",
                        strategy=name,
                        document_id=document_id,
                        error=str(exc),
                    )

        raise OCRError(
            f"All OCR strategies failed to extract text from document {document_id}"
        )
