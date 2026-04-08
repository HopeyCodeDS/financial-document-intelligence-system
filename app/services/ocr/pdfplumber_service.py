"""
pdfplumber-based OCR service for text-native PDFs.

Uses pdfplumber for high-quality extraction from PDFs with embedded text.
Preserves layout information (bounding boxes) for source traceability.
"""
from __future__ import annotations

import io
from typing import Any

import pdfplumber

from app.core.exceptions import OCRError, OCRPageExtractionError
from app.core.logging import get_logger
from app.schemas.ocr import BoundingBox, OCRResult, PageOCRResult, TextBlock
from app.services.ocr.base import AbstractOCRService

logger = get_logger(__name__)

# Minimum character count on a page to consider it "text-native"
_TEXT_NATIVE_THRESHOLD = 20


class PDFPlumberService(AbstractOCRService):
    """Extracts text and tables from PDFs that contain embedded text."""

    def can_handle(self, file_bytes: bytes) -> bool:
        """Return True if the PDF has extractable text on any page."""
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    if len(text.strip()) >= _TEXT_NATIVE_THRESHOLD:
                        return True
            return False
        except Exception:
            return False

    async def extract(self, file_bytes: bytes, document_id: str) -> OCRResult:
        """Extract text blocks and bounding boxes from all pages."""
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                pages = []
                for i, page in enumerate(pdf.pages, start=1):
                    try:
                        page_result = self._extract_page(page, i)
                        pages.append(page_result)
                    except Exception as exc:
                        raise OCRPageExtractionError(i, str(exc)) from exc

            logger.info(
                "pdfplumber_extraction_complete",
                document_id=document_id,
                page_count=len(pages),
            )
            return OCRResult.from_pages(document_id, pages, strategy="pdfplumber")

        except OCRError:
            raise
        except Exception as exc:
            raise OCRError(f"pdfplumber extraction failed: {exc}") from exc

    def _extract_page(self, page: Any, page_number: int) -> PageOCRResult:
        """Extract text blocks from a single pdfplumber Page object."""
        width = float(page.width) if page.width else None
        height = float(page.height) if page.height else None

        # Extract word-level tokens with bounding boxes
        blocks: list[TextBlock] = []
        words = page.extract_words(
            x_tolerance=3,
            y_tolerance=3,
            keep_blank_chars=False,
            use_text_flow=True,
        ) or []

        # Group words into line-level blocks
        if words and width and height:
            current_line: list[dict] = []
            current_y = None

            for word in words:
                word_y = round(word["top"], 1)
                if current_y is None or abs(word_y - current_y) > 5:
                    if current_line:
                        blocks.append(self._words_to_block(current_line, width, height))
                    current_line = [word]
                    current_y = word_y
                else:
                    current_line.append(word)

            if current_line:
                blocks.append(self._words_to_block(current_line, width, height))

        # Also extract tables as separate blocks
        for table in page.extract_tables() or []:
            table_text = "\n".join(
                " | ".join(cell or "" for cell in row) for row in table if row
            )
            if table_text.strip():
                blocks.append(TextBlock(text=table_text, block_type="table"))

        raw_text = page.extract_text() or ""
        return PageOCRResult(
            page_number=page_number,
            raw_text=raw_text,
            blocks=blocks,
            width=width,
            height=height,
        )

    @staticmethod
    def _words_to_block(
        words: list[dict], page_width: float, page_height: float
    ) -> TextBlock:
        text = " ".join(w["text"] for w in words)
        x0 = min(w["x0"] for w in words) / page_width
        y0 = min(w["top"] for w in words) / page_height
        x1 = max(w["x1"] for w in words) / page_width
        y1 = max(w["bottom"] for w in words) / page_height
        return TextBlock(
            text=text,
            bbox=BoundingBox(
                x0=max(0.0, min(1.0, x0)),
                y0=max(0.0, min(1.0, y0)),
                x1=max(0.0, min(1.0, x1)),
                y1=max(0.0, min(1.0, y1)),
            ),
            block_type="text",
        )
