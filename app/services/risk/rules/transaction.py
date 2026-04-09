"""
Transaction-level risk rules.
"""
from __future__ import annotations

from app.models.extraction import RiskLevel
from app.schemas.extraction import BankStatementExtraction, ExtractionPayload
from app.schemas.risk import AnomalyFlag
from app.services.risk.rules.base import AbstractRiskRule


class LargeTransferRule(AbstractRiskRule):
    """Flag individual transactions above the large transfer threshold."""

    @property
    def name(self) -> str:
        return "large_transfer"

    def execute(self, data: ExtractionPayload, thresholds: dict) -> list[AnomalyFlag]:
        if not isinstance(data, BankStatementExtraction):
            return []

        threshold = thresholds.get("large_transfer_threshold", 50_000.0)
        flags: list[AnomalyFlag] = []

        for i, txn in enumerate(data.transactions):
            amount = txn.amount
            if amount is not None and abs(amount) >= threshold:
                flags.append(AnomalyFlag(
                    rule_name=self.name,
                    risk_level=RiskLevel.high,
                    description=f"Transaction {i + 1}: amount {amount} exceeds large transfer threshold {threshold}",
                    field="transactions",
                    value=str(amount),
                    threshold=str(threshold),
                ))
        return flags


class RoundNumberRule(AbstractRiskRule):
    """Flag suspiciously round numbers (common in money laundering patterns)."""

    @property
    def name(self) -> str:
        return "round_number_amounts"

    def execute(self, data: ExtractionPayload, thresholds: dict) -> list[AnomalyFlag]:
        if not isinstance(data, BankStatementExtraction):
            return []

        threshold = thresholds.get("round_number_threshold", 10_000.0)
        flags: list[AnomalyFlag] = []

        for i, txn in enumerate(data.transactions):
            amount = txn.amount
            if amount is not None and abs(amount) >= threshold:
                if amount % 1000 == 0:  # multiple of 1000 = suspiciously round
                    flags.append(AnomalyFlag(
                        rule_name=self.name,
                        risk_level=RiskLevel.medium,
                        description=f"Transaction {i + 1}: suspiciously round amount {amount}",
                        field="transactions",
                        value=str(amount),
                        threshold=str(threshold),
                    ))
        return flags


class HighVelocityRule(AbstractRiskRule):
    """Flag when total transaction count exceeds velocity threshold."""

    @property
    def name(self) -> str:
        return "high_velocity"

    def execute(self, data: ExtractionPayload, thresholds: dict) -> list[AnomalyFlag]:
        if not isinstance(data, BankStatementExtraction):
            return []

        max_txns = thresholds.get("velocity_max_transactions", 20)
        txn_count = len(data.transactions)

        if txn_count > max_txns:
            return [AnomalyFlag(
                rule_name=self.name,
                risk_level=RiskLevel.medium,
                description=f"High transaction velocity: {txn_count} transactions exceeds threshold of {max_txns}",
                field="transactions",
                value=str(txn_count),
                threshold=str(max_txns),
            )]
        return []


class NegativeBalanceRule(AbstractRiskRule):
    """Flag negative closing balances (unexpected for most accounts)."""

    @property
    def name(self) -> str:
        return "negative_balance"

    def execute(self, data: ExtractionPayload, thresholds: dict) -> list[AnomalyFlag]:
        if not isinstance(data, BankStatementExtraction):
            return []

        closing = data.closing_balance.value
        if closing is not None and closing < 0:
            return [AnomalyFlag(
                rule_name=self.name,
                risk_level=RiskLevel.medium,
                description=f"Negative closing balance: {closing}",
                field="closing_balance",
                value=str(closing),
            )]
        return []
