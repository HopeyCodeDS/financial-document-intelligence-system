"""
Financial validation rules.

Validates monetary consistency in extracted data.
"""
from __future__ import annotations

from app.schemas.extraction import BankStatementExtraction, ExtractionPayload, InvoiceExtraction
from app.schemas.validation import RuleViolation, ViolationSeverity
from app.services.validation.rules.base import AbstractValidationRule

_BALANCE_TOLERANCE = 0.01  # 1 cent tolerance for floating-point arithmetic


class BalanceConsistencyRule(AbstractValidationRule):
    """
    Bank statement: opening_balance + credits - debits ≈ closing_balance.
    Allowed deviation: ±0.01 (rounding).
    """

    @property
    def name(self) -> str:
        return "balance_consistency"

    def execute(self, data: ExtractionPayload) -> list[RuleViolation]:
        if not isinstance(data, BankStatementExtraction):
            return []

        opening = data.opening_balance.value
        closing = data.closing_balance.value
        credits = data.total_credits.value
        debits = data.total_debits.value

        if any(v is None for v in [opening, closing, credits, debits]):
            return [RuleViolation(
                rule_name=self.name,
                severity=ViolationSeverity.warning,
                field="opening_balance / closing_balance",
                message="Cannot verify balance consistency — one or more balance fields are null",
            )]

        expected_closing = opening + credits - debits  # type: ignore[operator]
        diff = abs(expected_closing - closing)  # type: ignore[operator]
        if diff > _BALANCE_TOLERANCE:
            return [RuleViolation(
                rule_name=self.name,
                severity=ViolationSeverity.error,
                field="closing_balance",
                message=f"Balance inconsistency: opening({opening}) + credits({credits}) - debits({debits}) = {expected_closing:.2f}, but closing = {closing}",
                expected=f"{expected_closing:.2f}",
                actual=str(closing),
            )]
        return []


class InvoiceTotalsRule(AbstractValidationRule):
    """Invoice: subtotal + tax ≈ total_amount."""

    @property
    def name(self) -> str:
        return "invoice_totals_consistency"

    def execute(self, data: ExtractionPayload) -> list[RuleViolation]:
        if not isinstance(data, InvoiceExtraction):
            return []

        subtotal = data.subtotal.value
        tax = data.tax_amount.value
        total = data.total_amount.value

        if any(v is None for v in [subtotal, tax, total]):
            return [RuleViolation(
                rule_name=self.name,
                severity=ViolationSeverity.warning,
                field="total_amount",
                message="Cannot verify invoice total — one or more amount fields are null",
            )]

        expected = subtotal + tax  # type: ignore[operator]
        diff = abs(expected - total)  # type: ignore[operator]
        if diff > _BALANCE_TOLERANCE:
            return [RuleViolation(
                rule_name=self.name,
                severity=ViolationSeverity.error,
                field="total_amount",
                message=f"Invoice total inconsistency: subtotal({subtotal}) + tax({tax}) = {expected:.2f}, but total = {total}",
                expected=f"{expected:.2f}",
                actual=str(total),
            )]
        return []


class LineItemsTotalRule(AbstractValidationRule):
    """Invoice: sum of line item totals ≈ subtotal."""

    @property
    def name(self) -> str:
        return "line_items_total"

    def execute(self, data: ExtractionPayload) -> list[RuleViolation]:
        if not isinstance(data, InvoiceExtraction):
            return []
        if not data.line_items or data.subtotal.value is None:
            return []

        line_totals = [item.total for item in data.line_items if item.total is not None]
        if not line_totals:
            return []

        computed = sum(line_totals)
        diff = abs(computed - data.subtotal.value)
        if diff > _BALANCE_TOLERANCE:
            return [RuleViolation(
                rule_name=self.name,
                severity=ViolationSeverity.warning,
                field="line_items",
                message=f"Line item totals ({computed:.2f}) do not match subtotal ({data.subtotal.value})",
                expected=str(data.subtotal.value),
                actual=f"{computed:.2f}",
            )]
        return []


class NegativeAmountRule(AbstractValidationRule):
    """Flag unexpectedly negative amounts (e.g. negative totals on invoices)."""

    @property
    def name(self) -> str:
        return "negative_amount"

    def execute(self, data: ExtractionPayload) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        if isinstance(data, InvoiceExtraction):
            for field_name in ("subtotal", "tax_amount", "total_amount"):
                field = getattr(data, field_name)
                if field.value is not None and field.value < 0:
                    violations.append(RuleViolation(
                        rule_name=self.name,
                        severity=ViolationSeverity.warning,
                        field=field_name,
                        message=f"Unexpectedly negative amount: {field_name} = {field.value}",
                        actual=str(field.value),
                    ))
        return violations
