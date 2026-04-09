"""
RiskDetectionService — runs all risk rules and produces a RiskAssessment.
"""
from __future__ import annotations

from app.config import Settings
from app.core.logging import get_logger
from app.models.document import DocumentType
from app.models.extraction import RiskLevel
from app.schemas.extraction import ExtractionPayload
from app.schemas.risk import AnomalyFlag, RiskAssessment
from app.services.risk.rules.counterparty import (
    HighRiskJurisdictionRule,
    UnusualCounterpartyPatternRule,
)
from app.services.risk.rules.transaction import (
    HighVelocityRule,
    LargeTransferRule,
    NegativeBalanceRule,
    RoundNumberRule,
)

logger = get_logger(__name__)

_ALL_RULES = [
    LargeTransferRule(),
    RoundNumberRule(),
    HighVelocityRule(),
    NegativeBalanceRule(),
    HighRiskJurisdictionRule(),
    UnusualCounterpartyPatternRule(),
]

_LEVEL_ORDER = [RiskLevel.low, RiskLevel.medium, RiskLevel.high, RiskLevel.critical]

# Risk levels at or above this require human review
_REVIEW_THRESHOLD = RiskLevel.medium


class RiskDetectionService:
    def __init__(self, settings: Settings) -> None:
        self._thresholds = {
            "large_transfer_threshold": settings.risk_large_transfer_threshold,
            "round_number_threshold": settings.risk_round_number_threshold,
            "velocity_max_transactions": settings.risk_velocity_max_transactions,
        }

    def detect(
        self,
        data: ExtractionPayload,
        document_type: DocumentType,
    ) -> RiskAssessment:
        all_flags: list[AnomalyFlag] = []

        for rule in _ALL_RULES:
            try:
                flags = rule.execute(data, self._thresholds)
                all_flags.extend(flags)
            except Exception as exc:
                logger.exception(
                    "risk_rule_error",
                    rule=rule.name,
                    error=str(exc),
                )

        overall_level = self._compute_overall_level(all_flags)
        requires_review = _LEVEL_ORDER.index(overall_level) >= _LEVEL_ORDER.index(_REVIEW_THRESHOLD)

        summary = (
            f"{len(all_flags)} anomaly flag(s) detected. Overall risk: {overall_level.value}."
            if all_flags
            else "No anomalies detected."
        )

        logger.info(
            "risk_detection_complete",
            document_type=document_type.value,
            flag_count=len(all_flags),
            risk_level=overall_level.value,
            requires_review=requires_review,
        )

        return RiskAssessment(
            risk_level=overall_level,
            flags=all_flags,
            requires_review=requires_review,
            summary=summary,
        )

    @staticmethod
    def _compute_overall_level(flags: list[AnomalyFlag]) -> RiskLevel:
        if not flags:
            return RiskLevel.low
        # Highest level among all flags
        max_idx = max(_LEVEL_ORDER.index(f.risk_level) for f in flags)
        return _LEVEL_ORDER[max_idx]
