"""
Temporal validation rules — date ordering and period consistency.
"""
from __future__ import annotations

from datetime import date, datetime

from app.schemas.extraction import BankStatementExtraction, ExtractionPayload
from app.schemas.validation import RuleViolation, ViolationSeverity
from app.services.validation.rules.base import AbstractValidationRule


def _parse_date(value: object) -> date | None:
    if value is None or not isinstance(value, str):
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


class StatementPeriodOrderRule(AbstractValidationRule):
    """Bank statement: period_start must be before period_end."""

    @property
    def name(self) -> str:
        return "statement_period_order"

    def execute(self, data: ExtractionPayload) -> list[RuleViolation]:
        if not isinstance(data, BankStatementExtraction):
            return []

        start = _parse_date(data.statement_period_start.value)
        end = _parse_date(data.statement_period_end.value)

        if start is None or end is None:
            return []

        if start >= end:
            return [RuleViolation(
                rule_name=self.name,
                severity=ViolationSeverity.error,
                field="statement_period_start",
                message=f"Statement period start ({start}) must be before end ({end})",
                expected=f"< {end}",
                actual=str(start),
            )]
        return []


class FutureDateRule(AbstractValidationRule):
    """Flag dates that are unreasonably far in the future (potential parsing error)."""

    MAX_FUTURE_YEARS = 2

    @property
    def name(self) -> str:
        return "future_date"

    def execute(self, data: ExtractionPayload) -> list[RuleViolation]:
        today = date.today()
        violations: list[RuleViolation] = []

        for field_name, field_value in data.model_dump().items():
            if isinstance(field_value, dict) and "value" in field_value:
                parsed = _parse_date(field_value.get("value"))
                if parsed and (parsed.year - today.year) > self.MAX_FUTURE_YEARS:
                    violations.append(RuleViolation(
                        rule_name=self.name,
                        severity=ViolationSeverity.warning,
                        field=field_name,
                        message=f"Field '{field_name}' contains a date far in the future: {parsed}",
                        actual=str(parsed),
                    ))
        return violations
