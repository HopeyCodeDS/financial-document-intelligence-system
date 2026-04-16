"""
Pydantic schemas for risk and anomaly detection output.
"""
from __future__ import annotations


from pydantic import BaseModel

from app.models.extraction import RiskLevel


class AnomalyFlag(BaseModel):
    rule_name: str
    risk_level: RiskLevel
    description: str
    field: str | None = None
    value: str | None = None
    threshold: str | None = None


class RiskAssessment(BaseModel):
    risk_level: RiskLevel
    flags: list[AnomalyFlag]
    requires_review: bool
    summary: str

    @classmethod
    def low(cls) -> "RiskAssessment":
        return cls(
            risk_level=RiskLevel.low,
            flags=[],
            requires_review=False,
            summary="No anomalies detected",
        )
