"""
Domain exception hierarchy for FDIS.

All application-specific errors derive from FDISError so callers can catch
at any granularity. HTTP status codes are attached to exceptions that cross
the API boundary — FastAPI exception handlers translate these to responses.
"""
from __future__ import annotations

from typing import Any


class FDISError(Exception):
    """Base class for all FDIS domain errors."""

    message: str
    status_code: int = 500

    def __init__(self, message: str, **context: Any) -> None:
        self.message = message
        self.context = context
        super().__init__(message)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.message!r})"


# ── Document errors ───────────────────────────────────────────────────────────

class DocumentNotFoundError(FDISError):
    status_code = 404

    def __init__(self, document_id: str) -> None:
        super().__init__(f"Document not found: {document_id}", document_id=document_id)


class DocumentAlreadyExistsError(FDISError):
    status_code = 409

    def __init__(self, document_id: str) -> None:
        super().__init__(f"Document already exists: {document_id}", document_id=document_id)


class InvalidDocumentTypeError(FDISError):
    status_code = 422

    def __init__(self, document_type: str) -> None:
        super().__init__(
            f"Unsupported document type: {document_type!r}",
            document_type=document_type,
        )


class FileTooLargeError(FDISError):
    status_code = 413

    def __init__(self, size_bytes: int, max_bytes: int) -> None:
        super().__init__(
            f"File size {size_bytes} bytes exceeds maximum {max_bytes} bytes",
            size_bytes=size_bytes,
            max_bytes=max_bytes,
        )


class InvalidFileTypeError(FDISError):
    status_code = 415

    def __init__(self, content_type: str) -> None:
        super().__init__(
            f"Invalid file type: {content_type!r}. Only PDF files are accepted.",
            content_type=content_type,
        )


# ── OCR errors ────────────────────────────────────────────────────────────────

class OCRError(FDISError):
    """Raised when text extraction from a document fails."""
    status_code = 422


class OCRPageExtractionError(OCRError):
    def __init__(self, page_number: int, reason: str) -> None:
        super().__init__(
            f"Failed to extract page {page_number}: {reason}",
            page_number=page_number,
            reason=reason,
        )


# ── PII errors ────────────────────────────────────────────────────────────────

class PIIMaskingError(FDISError):
    """Raised when PII masking fails. Pipeline must halt — do not pass to LLM."""
    status_code = 500


class PIIDecryptionError(FDISError):
    """Raised when PII reverse-mapping decryption fails."""
    status_code = 500


# ── LLM errors ───────────────────────────────────────────────────────────────

class LLMExtractionError(FDISError):
    """Raised when the LLM call or response parsing fails."""
    status_code = 502


class LLMResponseParseError(LLMExtractionError):
    """LLM returned a response that could not be parsed into the expected schema."""

    def __init__(self, reason: str, raw_response: str = "") -> None:
        super().__init__(
            f"Failed to parse LLM response: {reason}",
            reason=reason,
            raw_response=raw_response[:500],  # truncate for safety
        )


class LLMRateLimitError(LLMExtractionError):
    status_code = 429


# ── Validation errors ─────────────────────────────────────────────────────────

class ValidationEngineError(FDISError):
    """Internal validation engine error (not a user input error)."""
    status_code = 500


# ── Risk errors ───────────────────────────────────────────────────────────────

class RiskDetectionError(FDISError):
    status_code = 500


# ── Storage errors ────────────────────────────────────────────────────────────

class StorageError(FDISError):
    status_code = 500


class FileNotFoundInStorageError(StorageError):
    status_code = 404

    def __init__(self, path: str) -> None:
        super().__init__(f"File not found in storage: {path}", path=path)


# ── Auth errors ───────────────────────────────────────────────────────────────

class AuthenticationError(FDISError):
    status_code = 401


class AuthorizationError(FDISError):
    status_code = 403


# ── Pipeline errors ───────────────────────────────────────────────────────────

class PipelineError(FDISError):
    """Raised when a critical pipeline step fails and execution must halt."""
    status_code = 500

    def __init__(self, step_name: str, reason: str) -> None:
        super().__init__(
            f"Pipeline step '{step_name}' failed: {reason}",
            step_name=step_name,
            reason=reason,
        )


# ── Audit errors ──────────────────────────────────────────────────────────────

class AuditLogError(FDISError):
    """Raised when the audit logger itself fails — should never be silently swallowed."""
    status_code = 500


# ── Review errors ─────────────────────────────────────────────────────────────

class ReviewTaskNotFoundError(FDISError):
    status_code = 404

    def __init__(self, task_id: str) -> None:
        super().__init__(f"Review task not found: {task_id}", task_id=task_id)


class ReviewAlreadyDecidedError(FDISError):
    status_code = 409

    def __init__(self, task_id: str, current_status: str) -> None:
        super().__init__(
            f"Review task {task_id} already has status '{current_status}'",
            task_id=task_id,
            current_status=current_status,
        )
