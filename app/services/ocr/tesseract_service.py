"""
Tesseract-based OCR service for image-only (scanned) PDFs.

Converts each PDF page to an image via pdf2image, then runs pytesseract.
Used as a fallback when pdfplumber finds no extractable text.
"""
from __future__ import annotations

import asyncio

from app.core.exceptions import OCRError, OCRPageExtractionError
from app.core.logging import get_logger
from app.schemas.ocr import BoundingBox, OCRResult, PageOCRResult, TextBlock
from app.services.ocr.base import AbstractOCRService

logger = get_logger(__name__)


class TesseractService(AbstractOCRService):
    """OCR fallback using Tesseract for scanned/image-based PDFs."""

    def __init__(self, dpi: int = 300, lang: str = "eng") -> None:
        self._dpi = dpi
        self._lang = lang

    def can_handle(self, file_bytes: bytes) -> bool:
        """Tesseract can always attempt OCR — it's the last-resort fallback."""
        return True

    async def extract(self, file_bytes: bytes, document_id: str) -> OCRResult:
        """Convert PDF pages to images and run Tesseract OCR on each."""
        loop = asyncio.get_event_loop()
        pages = await loop.run_in_executor(None, self._extract_sync, file_bytes, document_id)
        logger.info(
            "tesseract_extraction_complete",
            document_id=document_id,
            page_count=len(pages),
        )
        return OCRResult.from_pages(document_id, pages, strategy="tesseract")

    def _extract_sync(self, file_bytes: bytes, document_id: str) -> list[PageOCRResult]:
        """Synchronous extraction — runs in thread pool to avoid blocking event loop."""
        try:
            from pdf2image import convert_from_bytes
        except ImportError as exc:
            raise OCRError(f"Tesseract dependencies not installed: {exc}") from exc

        try:
            images = convert_from_bytes(file_bytes, dpi=self._dpi)
        except Exception as exc:
            raise OCRError(f"Failed to convert PDF to images: {exc}") from exc

        pages = []
        for i, image in enumerate(images, start=1):
            try:
                page_result = self._process_image(image, i)
                pages.append(page_result)
            except Exception as exc:
                raise OCRPageExtractionError(i, str(exc)) from exc

        return pages

    def _process_image(self, image: object, page_number: int) -> PageOCRResult:
        import pytesseract
        from PIL import Image

        img: Image.Image = image  # type: ignore[assignment]
        width, height = img.size

        # Full-page text
        raw_text: str = pytesseract.image_to_string(img, lang=self._lang)

        # Word-level data with bounding boxes and confidence
        data = pytesseract.image_to_data(
            img, lang=self._lang, output_type=pytesseract.Output.DICT
        )

        blocks: list[TextBlock] = []
        n_boxes = len(data["text"])
        for j in range(n_boxes):
            word = data["text"][j].strip()
            conf = int(data["conf"][j])
            if word and conf > 30:  # filter out low-confidence noise
                x = data["left"][j]
                y = data["top"][j]
                w = data["width"][j]
                h = data["height"][j]
                blocks.append(
                    TextBlock(
                        text=word,
                        bbox=BoundingBox(
                            x0=x / width,
                            y0=y / height,
                            x1=(x + w) / width,
                            y1=(y + h) / height,
                        ),
                        confidence=conf / 100.0,
                        block_type="text",
                    )
                )

        return PageOCRResult(
            page_number=page_number,
            raw_text=raw_text,
            blocks=blocks,
            width=float(width),
            height=float(height),
        )
