"""
Pydantic schemas for PII detection and masking output.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class PIIEntity(BaseModel):
    """A single detected PII entity."""

    entity_type: str       # e.g. "PERSON", "IBAN", "ACCOUNT_NUMBER"
    token: str             # replacement token e.g. "[PERSON_1]"
    start: int             # character offset in original text
    end: int               # character offset in original text
    score: float = Field(ge=0.0, le=1.0)   # detection confidence


class MaskingResult(BaseModel):
    """Output of the PII masking operation."""

    masked_text: str
    entities_found: list[PIIEntity]
    entity_count: int

    @classmethod
    def empty(cls, text: str) -> "MaskingResult":
        return cls(masked_text=text, entities_found=[], entity_count=0)
