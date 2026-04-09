"""
Counterparty and jurisdiction risk rules.
"""
from __future__ import annotations

from app.models.extraction import RiskLevel
from app.schemas.extraction import BankStatementExtraction, ExtractionPayload
from app.schemas.risk import AnomalyFlag
from app.services.risk.rules.base import AbstractRiskRule

# High-risk jurisdiction keywords (simplified — production would use a proper list)
_HIGH_RISK_KEYWORDS = frozenset({
    "offshore", "cayman", "bvi", "british virgin", "panama", "seychelles",
    "vanuatu", "samoa", "nauru", "anonymous", "bearer",
})


class HighRiskJurisdictionRule(AbstractRiskRule):
    """Flag transactions with counterparties in high-risk jurisdictions."""

    @property
    def name(self) -> str:
        return "high_risk_jurisdiction"

    def execute(self, data: ExtractionPayload, thresholds: dict) -> list[AnomalyFlag]:
        if not isinstance(data, BankStatementExtraction):
            return []

        flags: list[AnomalyFlag] = []
        for i, txn in enumerate(data.transactions):
            description = (txn.description or "").lower()
            for keyword in _HIGH_RISK_KEYWORDS:
                if keyword in description:
                    flags.append(AnomalyFlag(
                        rule_name=self.name,
                        risk_level=RiskLevel.high,
                        description=f"Transaction {i + 1}: potential high-risk jurisdiction keyword '{keyword}' in description",
                        field="transactions",
                        value=txn.description,
                    ))
                    break  # one flag per transaction
        return flags


class UnusualCounterpartyPatternRule(AbstractRiskRule):
    """Flag transactions where description contains structuring indicators."""

    _STRUCTURING_PATTERNS = [
        "cash deposit", "currency exchange", "money order",
        "wire transfer", "telegraphic transfer", "tt ",
    ]

    @property
    def name(self) -> str:
        return "unusual_counterparty_pattern"

    def execute(self, data: ExtractionPayload, thresholds: dict) -> list[AnomalyFlag]:
        if not isinstance(data, BankStatementExtraction):
            return []

        flags: list[AnomalyFlag] = []
        for i, txn in enumerate(data.transactions):
            description = (txn.description or "").lower()
            for pattern in self._STRUCTURING_PATTERNS:
                if pattern in description:
                    flags.append(AnomalyFlag(
                        rule_name=self.name,
                        risk_level=RiskLevel.medium,
                        description=f"Transaction {i + 1}: pattern '{pattern}' may warrant review",
                        field="transactions",
                        value=txn.description,
                    ))
                    break
        return flags
