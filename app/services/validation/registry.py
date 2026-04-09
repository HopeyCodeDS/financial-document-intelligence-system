"""
Validation rule registry — maps document types to their rule sets.
"""
from __future__ import annotations

from app.models.document import DocumentType
from app.services.validation.rules.base import AbstractValidationRule
from app.services.validation.rules.completeness import LowConfidenceRule, RequiredFieldsRule
from app.services.validation.rules.financial import (
    BalanceConsistencyRule,
    InvoiceTotalsRule,
    LineItemsTotalRule,
    NegativeAmountRule,
)
from app.services.validation.rules.temporal import FutureDateRule, StatementPeriodOrderRule

_REGISTRY: dict[DocumentType, list[AbstractValidationRule]] = {
    DocumentType.bank_statement: [
        RequiredFieldsRule(),
        LowConfidenceRule(),
        BalanceConsistencyRule(),
        StatementPeriodOrderRule(),
        FutureDateRule(),
    ],
    DocumentType.invoice: [
        RequiredFieldsRule(),
        LowConfidenceRule(),
        InvoiceTotalsRule(),
        LineItemsTotalRule(),
        NegativeAmountRule(),
        FutureDateRule(),
    ],
    DocumentType.portfolio: [
        RequiredFieldsRule(),
        LowConfidenceRule(),
        FutureDateRule(),
    ],
}


def get_rules(document_type: DocumentType) -> list[AbstractValidationRule]:
    return _REGISTRY.get(document_type, [RequiredFieldsRule(), LowConfidenceRule()])
