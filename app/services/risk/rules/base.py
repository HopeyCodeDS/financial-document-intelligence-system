"""
Abstract base class for risk detection rules.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.extraction import ExtractionPayload
from app.schemas.risk import AnomalyFlag


class AbstractRiskRule(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique rule identifier."""

    @abstractmethod
    def execute(
        self,
        data: ExtractionPayload,
        thresholds: dict,
    ) -> list[AnomalyFlag]:
        """
        Evaluate risk rule.

        Returns a (possibly empty) list of AnomalyFlags.
        Must never raise — catch internally.
        """
