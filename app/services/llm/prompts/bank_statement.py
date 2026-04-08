"""
Prompt template and tool schema for bank statement extraction.
"""
from __future__ import annotations

SYSTEM_PROMPT = """You are a precise financial document parser specialising in bank statements.

Rules you MUST follow:
1. Extract ONLY information explicitly present in the document text.
2. If a field is absent or unclear, set value to null and confidence to 0.0.
3. NEVER infer, interpolate, or hallucinate values.
4. All monetary amounts must be extracted as numbers (no currency symbols).
5. Dates must be in ISO 8601 format (YYYY-MM-DD) where possible.
6. PII tokens like [PERSON_1] or [IBAN_1] must be preserved exactly as-is — do not replace them.
7. For each field, provide a confidence score [0.0–1.0] and a brief reasoning explaining the source.

You will use the extract_bank_statement tool to return structured data."""

TOOL_DEFINITION = {
    "name": "extract_bank_statement",
    "description": "Extract all structured fields from a bank statement document.",
    "input_schema": {
        "type": "object",
        "properties": {
            "account_holder": {
                "type": "object",
                "properties": {
                    "value": {"type": ["string", "null"]},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "reasoning": {"type": ["string", "null"]},
                    "source_page": {"type": ["integer", "null"]},
                },
                "required": ["value", "confidence"],
            },
            "account_number": {
                "type": "object",
                "properties": {
                    "value": {"type": ["string", "null"]},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "reasoning": {"type": ["string", "null"]},
                    "source_page": {"type": ["integer", "null"]},
                },
                "required": ["value", "confidence"],
            },
            "bank_name": {
                "type": "object",
                "properties": {
                    "value": {"type": ["string", "null"]},
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
            "statement_period_start": {
                "type": "object",
                "properties": {
                    "value": {"type": ["string", "null"]},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": ["string", "null"]},
                    "source_page": {"type": ["integer", "null"]},
                },
                "required": ["value", "confidence"],
            },
            "statement_period_end": {
                "type": "object",
                "properties": {
                    "value": {"type": ["string", "null"]},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": ["string", "null"]},
                    "source_page": {"type": ["integer", "null"]},
                },
                "required": ["value", "confidence"],
            },
            "opening_balance": {
                "type": "object",
                "properties": {
                    "value": {"type": ["number", "null"]},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": ["string", "null"]},
                    "source_page": {"type": ["integer", "null"]},
                },
                "required": ["value", "confidence"],
            },
            "closing_balance": {
                "type": "object",
                "properties": {
                    "value": {"type": ["number", "null"]},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": ["string", "null"]},
                    "source_page": {"type": ["integer", "null"]},
                },
                "required": ["value", "confidence"],
            },
            "total_debits": {
                "type": "object",
                "properties": {
                    "value": {"type": ["number", "null"]},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": ["string", "null"]},
                    "source_page": {"type": ["integer", "null"]},
                },
                "required": ["value", "confidence"],
            },
            "total_credits": {
                "type": "object",
                "properties": {
                    "value": {"type": ["number", "null"]},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": ["string", "null"]},
                    "source_page": {"type": ["integer", "null"]},
                },
                "required": ["value", "confidence"],
            },
            "transactions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": ["string", "null"]},
                        "description": {"type": ["string", "null"]},
                        "amount": {"type": ["number", "null"]},
                        "currency": {"type": ["string", "null"]},
                        "debit": {"type": ["boolean", "null"]},
                        "balance_after": {"type": ["number", "null"]},
                        "reference": {"type": ["string", "null"]},
                    },
                },
            },
        },
        "required": [
            "account_holder", "account_number", "bank_name", "currency",
            "statement_period_start", "statement_period_end",
            "opening_balance", "closing_balance", "total_debits", "total_credits",
        ],
    },
}
