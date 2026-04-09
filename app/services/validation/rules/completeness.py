"""
Completeness validation rules — check required fields are present.
"""
from __future__ import annotations

from app.schemas.extraction import (
    BankStatementExtraction,
    ExtractionPayload,
    InvoiceExtraction,
    PortfolioExtraction,
)
from app.schemas.validation import RuleViolation, ViolationSeverity
from app.services.validation.rules.base import AbstractValidationRule

_BANK_REQUIRED = [
    "account_holder", "bank_name", "currency",
    "statement_period_start", "statement_period_end",
    "opening_balance", "closing_balance",
]
_INVOICE_REQUIRED = [
    "vendor_name", "invoice_number", "invoice_date",
    "currency", "total_amount",
]
_PORTFOLIO_REQUIRED = [
    "client_reference", "valuation_date", "total_value", "currency",
]


class RequiredFieldsRule(AbstractValidationRule):
    """Verify that all mandatory fields were extracted with non-null values."""

    @property
    def name(self) -> str:
        return "required_fields"

    def execute(self, data: ExtractionPayload) -> list[RuleViolation]:
        if isinstance(data, BankStatementExtraction):
            required = _BANK_REQUIRED
        elif isinstance(data, InvoiceExtraction):
            required = _INVOICE_REQUIRED
        elif isinstance(data, PortfolioExtraction):
            required = _PORTFOLIO_REQUIRED
        else:
            return []

        violations: list[RuleViolation] = []
        for field_name in required:
            field = getattr(data, field_name, None)
            if field is None or (hasattr(field, "value") and field.value is None):
                violations.append(RuleViolation(
                    rule_name=self.name,
                    severity=ViolationSeverity.error,
                    field=field_name,
                    message=f"Required field '{field_name}' is missing or null",
                ))
        return violations


class LowConfidenceRule(AbstractValidationRule):
    """Flag fields where extraction confidence is below threshold."""

    THRESHOLD = 0.5

    @property
    def name(self) -> str:
        return "low_confidence_fields"

    def execute(self, data: ExtractionPayload) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        for field_name, field_value in data.model_dump().items():
            if isinstance(field_value, dict) and "confidence" in field_value:
                conf = field_value.get("confidence", 1.0)
                if conf < self.THRESHOLD:
                    violations.append(RuleViolation(
                        rule_name=self.name,
                        severity=ViolationSeverity.warning,
                        field=field_name,
                        message=f"Field '{field_name}' has low extraction confidence: {conf:.2f}",
                        actual=f"{conf:.2f}",
                        expected=f">= {self.THRESHOLD}",
                    ))
        return violations
