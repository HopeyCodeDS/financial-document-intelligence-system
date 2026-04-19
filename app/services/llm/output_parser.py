"""
LLM output parser — validates and coerces Claude's tool_use input into Pydantic models.

Never trusts the raw LLM output. Always validates against a Pydantic schema.
Returns a structured result with an overall confidence score.
"""
from __future__ import annotations

import statistics
from typing import Any

from pydantic import ValidationError

from app.core.exceptions import LLMResponseParseError
from app.core.logging import get_logger
from app.models.document import DocumentType
from app.schemas.extraction import (
    BankStatementExtraction,
    ExtractionPayload,
    InvoiceExtraction,
    PortfolioExtraction,
)

logger = get_logger(__name__)

_SCHEMA_MAP: dict[DocumentType, type[ExtractionPayload]] = {
    DocumentType.bank_statement: BankStatementExtraction,
    DocumentType.invoice: InvoiceExtraction,
    DocumentType.portfolio: PortfolioExtraction,
}


def parse_llm_output(
    raw_input: dict[str, Any],
    document_type: DocumentType,
) -> tuple[ExtractionPayload, dict[str, float], float]:
    """
    Validate and parse Claude's tool_use input dict.

    Args:
        raw_input: The tool_use.input dict from Claude's response.
        document_type: Expected document type schema to validate against.

    Returns:
        (parsed_model, confidence_scores_dict, overall_confidence)

    Raises:
        LLMResponseParseError: If the input cannot be coerced into the schema.
    """
    schema_class = _SCHEMA_MAP.get(document_type)
    if schema_class is None:
        raise LLMResponseParseError(f"No schema for document type: {document_type}")

    # Ensure null fields have a minimum FieldExtraction structure
    sanitized = _sanitize_input(raw_input)

    try:
        model = schema_class.model_validate(sanitized)
    except ValidationError as exc:
        logger.warning(
            "llm_output_validation_error",
            document_type=document_type.value,
            errors=exc.errors(),
        )
        raise LLMResponseParseError(
            reason=f"Pydantic validation failed: {exc.error_count()} errors",
            raw_response=str(raw_input)[:500],
        ) from exc

    confidence_scores = _extract_confidence_scores(model)
    overall = statistics.mean(confidence_scores.values()) if confidence_scores else 0.0

    logger.info(
        "llm_output_parsed",
        document_type=document_type.value,
        field_count=len(confidence_scores),
        overall_confidence=round(overall, 3),
    )

    return model, confidence_scores, overall


def _sanitize_input(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Ensure every field that should be a FieldExtraction dict has the required keys.
    Fills in defaults rather than crashing on minor LLM formatting variations.
    """
    sanitized: dict[str, Any] = {}
    for key, value in raw.items():
        if isinstance(value, dict) and "confidence" in value:
            if "value" not in value:
                value = {**value, "value": None}
            sanitized[key] = value
        else:
            sanitized[key] = value
    return sanitized


def _extract_confidence_scores(model: ExtractionPayload) -> dict[str, float]:
    """Walk the model and collect per-field confidence scores."""
    scores: dict[str, float] = {}
    for field_name, field_value in model.model_dump().items():
        if isinstance(field_value, dict) and "confidence" in field_value:
            scores[field_name] = float(field_value.get("confidence", 0.0))
    return scores
