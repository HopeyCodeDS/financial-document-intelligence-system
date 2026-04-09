"""
Abstract base class for all validation rules.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.extraction import ExtractionPayload
from app.schemas.validation import RuleViolation


class AbstractValidationRule(ABC):
    """Stateless validation rule that operates on extracted data."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this rule, used in violation reports."""

    @abstractmethod
    def execute(self, data: ExtractionPayload) -> list[RuleViolation]:
        """
        Run validation logic.

        Returns a (possibly empty) list of violations.
        Rules must never raise exceptions — catch internally and return a violation.
        """
