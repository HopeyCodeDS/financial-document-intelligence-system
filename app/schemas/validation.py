"""
Pydantic schemas for validation engine output.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class ViolationSeverity(str, Enum):
    error = "error"     # blocks approval
    warning = "warning" # flags for human review


class RuleViolation(BaseModel):
    rule_name: str
    severity: ViolationSeverity
    field: str | None = None
    message: str
    expected: str | None = None
    actual: str | None = None


class ValidationResult(BaseModel):
    passed: bool
    violations: list[RuleViolation]
    error_count: int
    warning_count: int

    @classmethod
    def from_violations(cls, violations: list[RuleViolation]) -> "ValidationResult":
        errors = sum(1 for v in violations if v.severity == ViolationSeverity.error)
        warnings = sum(1 for v in violations if v.severity == ViolationSeverity.warning)
        return cls(
            passed=errors == 0,
            violations=violations,
            error_count=errors,
            warning_count=warnings,
        )
