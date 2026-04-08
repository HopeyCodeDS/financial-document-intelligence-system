"""
Pydantic schemas for LLM extraction output.

Every extracted field carries:
- value: the extracted data
- confidence: [0, 1] how certain the model is
- reasoning: optional explanation of the source evidence
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FieldExtraction(BaseModel):
    """A single extracted field with confidence and source traceability."""

    value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str | None = None
    source_page: int | None = None


class TransactionItem(BaseModel):
    date: str | None = None
    description: str | None = None
    amount: float | None = None
    currency: str | None = None
    debit: bool | None = None  # True = debit, False = credit
    balance_after: float | None = None
    reference: str | None = None


class BankStatementExtraction(BaseModel):
    account_holder: FieldExtraction
    account_number: FieldExtraction
    bank_name: FieldExtraction
    currency: FieldExtraction
    statement_period_start: FieldExtraction
    statement_period_end: FieldExtraction
    opening_balance: FieldExtraction
    closing_balance: FieldExtraction
    transactions: list[TransactionItem] = Field(default_factory=list)
    total_debits: FieldExtraction
    total_credits: FieldExtraction


class LineItem(BaseModel):
    description: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    total: float | None = None
    vat_rate: float | None = None


class InvoiceExtraction(BaseModel):
    vendor_name: FieldExtraction
    vendor_address: FieldExtraction
    invoice_number: FieldExtraction
    invoice_date: FieldExtraction
    due_date: FieldExtraction
    currency: FieldExtraction
    subtotal: FieldExtraction
    tax_amount: FieldExtraction
    total_amount: FieldExtraction
    line_items: list[LineItem] = Field(default_factory=list)
    payment_terms: FieldExtraction


class Holding(BaseModel):
    asset_name: str | None = None
    isin: str | None = None
    quantity: float | None = None
    price: float | None = None
    market_value: float | None = None
    currency: str | None = None
    weight_percent: float | None = None


class PortfolioExtraction(BaseModel):
    client_reference: FieldExtraction
    client_name: FieldExtraction
    valuation_date: FieldExtraction
    total_value: FieldExtraction
    currency: FieldExtraction
    holdings: list[Holding] = Field(default_factory=list)
    benchmark: FieldExtraction
    performance_ytd: FieldExtraction


# Union type for all document types
ExtractionPayload = BankStatementExtraction | InvoiceExtraction | PortfolioExtraction
