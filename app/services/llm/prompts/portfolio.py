"""
Prompt template and tool schema for portfolio summary extraction.
"""
from __future__ import annotations

SYSTEM_PROMPT = """You are a precise financial document parser specialising in portfolio statements.

Rules you MUST follow:
1. Extract ONLY information explicitly present in the document text.
2. If a field is absent or unclear, set value to null and confidence to 0.0.
3. NEVER infer, interpolate, or hallucinate values.
4. Monetary amounts must be numbers (no currency symbols).
5. Dates must be ISO 8601 (YYYY-MM-DD) where possible.
6. PII tokens like [PERSON_1] must be preserved exactly as-is — client identity is masked.
7. ISINs should be in standard 12-character format.
8. Holdings should capture every line in the portfolio table.

Use the extract_portfolio tool to return structured data."""

TOOL_DEFINITION = {
    "name": "extract_portfolio",
    "description": "Extract all structured fields from a portfolio summary statement.",
    "input_schema": {
        "type": "object",
        "properties": {
            "client_reference": {
                "type": "object",
                "properties": {
                    "value": {"type": ["string", "null"]},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": ["string", "null"]},
                    "source_page": {"type": ["integer", "null"]},
                },
                "required": ["value", "confidence"],
            },
            "client_name": {
                "type": "object",
                "properties": {
                    "value": {"type": ["string", "null"]},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": ["string", "null"]},
                    "source_page": {"type": ["integer", "null"]},
                },
                "required": ["value", "confidence"],
            },
            "valuation_date": {
                "type": "object",
                "properties": {
                    "value": {"type": ["string", "null"]},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": ["string", "null"]},
                    "source_page": {"type": ["integer", "null"]},
                },
                "required": ["value", "confidence"],
            },
            "total_value": {
                "type": "object",
                "properties": {
                    "value": {"type": ["number", "null"]},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": ["string", "null"]},
                    "source_page": {"type": ["integer", "null"]},
                },
                "required": ["value", "confidence"],
            },
            "currency": {
                "type": "object",
                "properties": {
                    "value": {"type": ["string", "null"]},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": ["string", "null"]},
                    "source_page": {"type": ["integer", "null"]},
                },
                "required": ["value", "confidence"],
            },
            "benchmark": {
                "type": "object",
                "properties": {
                    "value": {"type": ["string", "null"]},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": ["string", "null"]},
                    "source_page": {"type": ["integer", "null"]},
                },
                "required": ["value", "confidence"],
            },
            "performance_ytd": {
                "type": "object",
                "properties": {
                    "value": {"type": ["number", "null"]},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": ["string", "null"]},
                    "source_page": {"type": ["integer", "null"]},
                },
                "required": ["value", "confidence"],
            },
            "holdings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "asset_name": {"type": ["string", "null"]},
                        "isin": {"type": ["string", "null"]},
                        "quantity": {"type": ["number", "null"]},
                        "price": {"type": ["number", "null"]},
                        "market_value": {"type": ["number", "null"]},
                        "currency": {"type": ["string", "null"]},
                        "weight_percent": {"type": ["number", "null"]},
                    },
                },
            },
        },
        "required": [
            "client_reference", "client_name", "valuation_date",
            "total_value", "currency", "benchmark", "performance_ytd",
        ],
    },
}
