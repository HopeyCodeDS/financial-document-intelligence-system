"""
ValidationEngine — runs all rules for a document type and aggregates results.

Collects all violations (no fail-fast) for a complete picture for human review.
"""
from __future__ import annotations

from app.core.logging import get_logger
from app.models.document import DocumentType
from app.schemas.extraction import ExtractionPayload
from app.schemas.validation import ValidationResult
from app.services.validation.registry import get_rules

logger = get_logger(__name__)


class ValidationEngine:
    def run(
        self,
        data: ExtractionPayload,
        document_type: DocumentType,
    ) -> ValidationResult:
        """
        Run all rules for the given document type.

        Never raises — rule errors are caught and reported as violations.
        """
        rules = get_rules(document_type)
        all_violations = []

        for rule in rules:
            try:
                violations = rule.execute(data)
                all_violations.extend(violations)
            except Exception as exc:
                logger.exception(
                    "validation_rule_error",
                    rule=rule.name,
                    document_type=document_type.value,
                    error=str(exc),
                )
                # Report rule failure as a warning — don't silently swallow
                from app.schemas.validation import RuleViolation, ViolationSeverity
                all_violations.append(RuleViolation(
                    rule_name=rule.name,
                    severity=ViolationSeverity.warning,
                    message=f"Rule '{rule.name}' encountered an internal error: {exc}",
                ))

        result = ValidationResult.from_violations(all_violations)
        logger.info(
            "validation_complete",
            document_type=document_type.value,
            passed=result.passed,
            errors=result.error_count,
            warnings=result.warning_count,
        )
        return result
