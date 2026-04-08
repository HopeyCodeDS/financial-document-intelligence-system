"""
Abstract OCR service interface.

All concrete implementations must satisfy this contract.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.ocr import OCRResult


class AbstractOCRService(ABC):
    """Base class for OCR strategies."""

    @abstractmethod
    async def extract(self, file_bytes: bytes, document_id: str) -> OCRResult:
        """Extract text and layout from raw PDF bytes.

        Args:
            file_bytes: Raw PDF file content.
            document_id: UUID string for logging and result tagging.

        Returns:
            OCRResult with per-page text blocks and bounding boxes.

        Raises:
            OCRError: If extraction fails entirely.
        """

    @abstractmethod
    def can_handle(self, file_bytes: bytes) -> bool:
        """Return True if this strategy can extract usable text from the PDF.

        Used by the router to select the appropriate strategy.
        Native-text PDFs return True for pdfplumber; image-only PDFs do not.
        """
