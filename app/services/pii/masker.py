"""
PIIMaskingService — detects and replaces PII in OCR text before LLM calls.

Strategy:
- Uses Microsoft Presidio for detection (spaCy NER + pattern matching)
- Deterministic token replacement: [PERSON_1], [IBAN_1], etc.
- Builds a {token: original_value} mapping that is AES-256 encrypted and stored
- The LLM NEVER sees raw PII values — only tokens

Critical: this service is a hard gate in the pipeline. If it fails,
the pipeline must halt rather than passing unmasked text to the LLM.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Optional

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from app.core.exceptions import PIIMaskingError
from app.core.logging import get_logger
from app.schemas.pii import MaskingResult, PIIEntity
from app.services.pii.recognizers import get_custom_recognizers

logger = get_logger(__name__)

# Entity types to detect — ordered by priority
SUPPORTED_ENTITIES = [
    "PERSON",
    "IBAN",
    "ACCOUNT_NUMBER",
    "SWISS_BANKING_ID",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "LOCATION",
    "DATE_TIME",
    "NRP",  # Nationality, religious, political
]


class PIIMaskingService:
    """
    Detects and masks PII in text using Microsoft Presidio.

    Thread-safe — Presidio engines are stateless per call.
    """

    def __init__(self) -> None:
        self._analyzer: AnalyzerEngine | None = None
        self._anonymizer = AnonymizerEngine()

    def _get_analyzer(self) -> AnalyzerEngine:
        """Lazily initialise Presidio analyzer with custom recognizers."""
        if self._analyzer is None:
            registry = RecognizerRegistry()
            registry.load_predefined_recognizers(languages=["en"])
            for recognizer in get_custom_recognizers():
                registry.add_recognizer(recognizer)
            self._analyzer = AnalyzerEngine(registry=registry)
            logger.info("presidio_analyzer_initialised")
        return self._analyzer

    def mask(self, text: str, language: str = "en") -> tuple[MaskingResult, dict[str, str]]:
        """
        Detect and replace PII in text.

        Returns:
            (MaskingResult, reverse_mapping)
            where reverse_mapping = {"[PERSON_1]": "John Smith", ...}

        Raises:
            PIIMaskingError: If detection or replacement fails.
        """
        if not text.strip():
            return MaskingResult.empty(text), {}

        try:
            analyzer = self._get_analyzer()
            results = analyzer.analyze(
                text=text,
                entities=SUPPORTED_ENTITIES,
                language=language,
                score_threshold=0.5,
            )
        except Exception as exc:
            raise PIIMaskingError(f"Presidio analysis failed: {exc}") from exc

        if not results:
            return MaskingResult.empty(text), {}

        try:
            # Build per-entity-type counters for deterministic token naming
            type_counters: dict[str, int] = defaultdict(int)
            token_map: dict[str, str] = {}  # token -> operator config
            reverse_map: dict[str, str] = {}  # token -> original value

            operators: dict[str, OperatorConfig] = {}

            # Sort by start position to assign numbers in reading order
            sorted_results = sorted(results, key=lambda r: r.start)

            for result in sorted_results:
                entity_type = result.entity_type
                type_counters[entity_type] += 1
                token = f"[{entity_type}_{type_counters[entity_type]}]"

                original_value = text[result.start:result.end]
                reverse_map[token] = original_value

                # Use Presidio's replace operator with our deterministic token
                operators[entity_type] = OperatorConfig("replace", {"new_value": token})

            anonymized = self._anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators=operators,
            )

            entities = [
                PIIEntity(
                    entity_type=r.entity_type,
                    token=f"[{r.entity_type}_{list(sorted_results).index(r) + 1}]",
                    start=r.start,
                    end=r.end,
                    score=r.score,
                )
                for r in sorted_results
            ]

            result_obj = MaskingResult(
                masked_text=anonymized.text,
                entities_found=entities,
                entity_count=len(entities),
            )

            logger.info(
                "pii_masking_complete",
                entity_count=len(entities),
                entity_types=list(type_counters.keys()),
            )

            return result_obj, reverse_map

        except PIIMaskingError:
            raise
        except Exception as exc:
            raise PIIMaskingError(f"Presidio anonymization failed: {exc}") from exc

    def validate_no_pii_leakage(self, masked_text: str) -> bool:
        """
        Secondary check: verify no PII patterns remain in masked text.

        Runs a lightweight regex scan for common financial PII patterns.
        Does NOT call the full Presidio pipeline — fast enough for inline use.

        Returns True if no obvious leakage detected (text is safe for LLM).
        """
        # Basic IBAN pattern check
        iban_pattern = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
        if iban_pattern.search(masked_text):
            logger.warning("pii_leakage_detected", pattern="IBAN")
            return False

        # Long digit sequences (potential account numbers)
        account_pattern = re.compile(r"\b\d{10,18}\b")
        if account_pattern.search(masked_text):
            logger.warning("pii_leakage_detected", pattern="ACCOUNT_NUMBER")
            return False

        return True
