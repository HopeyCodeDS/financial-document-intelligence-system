"""
Custom Presidio recognizers for financial PII entities.

Supplements the built-in recognizers with financial-domain patterns:
- IBAN (ISO 13616)
- Generic account numbers
- Swiss banking identifiers
"""
from __future__ import annotations


from presidio_analyzer import Pattern, PatternRecognizer


class IBANRecognizer(PatternRecognizer):
    """Recognises International Bank Account Numbers (ISO 13616)."""

    PATTERNS = [
        Pattern(
            name="IBAN",
            regex=r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b",
            score=0.85,
        )
    ]
    CONTEXT = ["iban", "account", "bank", "bic", "swift"]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="IBAN",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
        )


class AccountNumberRecognizer(PatternRecognizer):
    """Recognises generic bank account numbers (8–18 digits, often hyphenated)."""

    PATTERNS = [
        Pattern(
            name="ACCOUNT_NUMBER_HYPHENATED",
            regex=r"\b\d{2,6}-\d{2,6}-\d{2,6}\b",
            score=0.7,
        ),
        Pattern(
            name="ACCOUNT_NUMBER_PLAIN",
            regex=r"\b\d{10,18}\b",
            score=0.5,
        ),
    ]
    CONTEXT = ["account", "acc", "acct", "number", "no", "reference", "ref"]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="ACCOUNT_NUMBER",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
        )


class SwissBankingRecognizer(PatternRecognizer):
    """Recognises Swiss-specific identifiers (clearing number, client number)."""

    PATTERNS = [
        Pattern(
            name="SWISS_CLEARING",
            regex=r"\b\d{3,5}-\d{1,4}\b",  # Swiss clearing number format
            score=0.6,
        ),
        Pattern(
            name="SWISS_BC_NUMBER",
            regex=r"\bBC\s*\d{4,6}\b",
            score=0.75,
        ),
    ]
    CONTEXT = ["clearing", "bc", "bank code", "ubs", "credit suisse", "postfinance"]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="SWISS_BANKING_ID",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
        )


def get_custom_recognizers() -> list[PatternRecognizer]:
    """Return all custom financial recognizers for registration with Presidio."""
    return [
        IBANRecognizer(),
        AccountNumberRecognizer(),
        SwissBankingRecognizer(),
    ]
