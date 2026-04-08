"""
Pydantic schemas for OCR extraction output.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Normalised bounding box [0,1] — x0, y0, x1, y1 (top-left origin)."""

    x0: float = Field(ge=0.0, le=1.0)
    y0: float = Field(ge=0.0, le=1.0)
    x1: float = Field(ge=0.0, le=1.0)
    y1: float = Field(ge=0.0, le=1.0)


class TextBlock(BaseModel):
    """A continuous block of text on a page, with optional location."""

    text: str
    bbox: BoundingBox | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    block_type: str = "text"  # "text" | "table" | "header" | "footer"


class PageOCRResult(BaseModel):
    """Extracted content from a single PDF page."""

    page_number: int = Field(ge=1)
    raw_text: str
    blocks: list[TextBlock] = Field(default_factory=list)
    width: float | None = None   # points
    height: float | None = None  # points


class OCRResult(BaseModel):
    """Full OCR output for a document."""

    document_id: str
    page_count: int
    pages: list[PageOCRResult]
    strategy_used: str  # "pdfplumber" | "doctr" | "tesseract"
    full_text: str       # concatenation of all pages for downstream use

    @classmethod
    def from_pages(cls, document_id: str, pages: list[PageOCRResult], strategy: str) -> "OCRResult":
        full_text = "\n\n".join(p.raw_text for p in pages)
        return cls(
            document_id=document_id,
            page_count=len(pages),
            pages=pages,
            strategy_used=strategy,
            full_text=full_text,
        )
