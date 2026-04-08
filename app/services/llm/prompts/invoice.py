"""
Prompt template and tool schema for invoice extraction.
"""
from __future__ import annotations

SYSTEM_PROMPT = """You are a precise financial document parser specialising in invoices.

Rules you MUST follow:
1. Extract ONLY information explicitly present in the document text.
2. If a field is absent or unclear, set value to null and confidence to 0.0.
3. NEVER infer, interpolate, or hallucinate values.
4. Monetary amounts must be numbers (no currency symbols).
5. Dates must be ISO 8601 (YYYY-MM-DD) where possible.
6. PII tokens like [PERSON_1] or [IBAN_1] must be preserved exactly as-is.
7. Line items should capture every row in the invoice table.

Use the extract_invoice tool to return structured data."""

TOOL_DEFINITION = {
    "name": "extract_invoice",
    "description": "Extract all structured fields from an invoice document.",
    "input_schema": {
        "type": "object",
        "properties": {
            "vendor_name": {
                "type": "object",
                "properties": {
                    "value": {"type": ["string", "null"]},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": ["string", "null"]},
                    "source_page": {"type": ["integer", "null"]},
                },
                "required": ["value", "confidence"],
            },
            "vendor_address": {
                "type": "object",
                "properties": {
                    "value": {"type": ["string", "null"]},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": ["string", "null"]},
                    "source_page": {"type": ["integer", "null"]},
                },
                "required": ["value", "confidence"],
            },
            "invoice_number": {
                "type": "object",
                "properties": {
                    "value": {"type": ["string", "null"]},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": ["string", "null"]},
                    "source_page": {"type": ["integer", "null"]},
                },
                "required": ["value", "confidence"],
            },
            "invoice_date": {
                "type": "object",
                "properties": {
                    "value": {"type": ["string", "null"]},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": ["string", "null"]},
                    "source_page": {"type": ["integer", "null"]},
                },
                "required": ["value", "confidence"],
            },
            "due_date": {
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
            "subtotal": {
                "type": "object",
                "properties": {
                    "value": {"type": ["number", "null"]},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": ["string", "null"]},
                    "source_page": {"type": ["integer", "null"]},
                },
                "required": ["value", "confidence"],
            },
            "tax_amount": {
                "type": "object",
                "properties": {
                    "value": {"type": ["number", "null"]},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": ["string", "null"]},
                    "source_page": {"type": ["integer", "null"]},
                },
                "required": ["value", "confidence"],
            },
            "total_amount": {
                "type": "object",
                "properties": {
                    "value": {"type": ["number", "null"]},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": ["string", "null"]},
                    "source_page": {"type": ["integer", "null"]},
                },
                "required": ["value", "confidence"],
            },
            "payment_terms": {
                "type": "object",
                "properties": {
                    "value": {"type": ["string", "null"]},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": ["string", "null"]},
                    "source_page": {"type": ["integer", "null"]},
                },
                "required": ["value", "confidence"],
            },
            "line_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": ["string", "null"]},
                        "quantity": {"type": ["number", "null"]},
                        "unit_price": {"type": ["number", "null"]},
                        "total": {"type": ["number", "null"]},
                        "vat_rate": {"type": ["number", "null"]},
                    },
                },
            },
        },
        "required": [
            "vendor_name", "vendor_address", "invoice_number", "invoice_date",
            "due_date", "currency", "subtotal", "tax_amount", "total_amount",
            "payment_terms",
        ],
    },
}
