"""
LLMExtractionService — orchestrates the LLM call, parsing, and result assembly.

Provider-agnostic: works with both Anthropic (Claude) and Ollama (Qwen, Llama, etc.)
via the AbstractLLMClient interface. The active provider is selected in config.
"""
from __future__ import annotations

from datetime import UTC, datetime

from app.config import LLMProvider, Settings
from app.core.logging import get_logger
from app.models.document import DocumentType
from app.schemas.extraction import ExtractionPayload
from app.services.llm.base import AbstractLLMClient
from app.services.llm.output_parser import parse_llm_output

logger = get_logger(__name__)

_PROMPT_MODULES: dict[DocumentType, object] = {}


def _get_prompt_module(document_type: DocumentType) -> object:
    global _PROMPT_MODULES
    if document_type not in _PROMPT_MODULES:
        if document_type == DocumentType.bank_statement:
            from app.services.llm.prompts import bank_statement
            _PROMPT_MODULES[document_type] = bank_statement
        elif document_type == DocumentType.invoice:
            from app.services.llm.prompts import invoice
            _PROMPT_MODULES[document_type] = invoice
        elif document_type == DocumentType.portfolio:
            from app.services.llm.prompts import portfolio
            _PROMPT_MODULES[document_type] = portfolio
        else:
            raise ValueError(f"No prompt module for document type: {document_type}")
    return _PROMPT_MODULES[document_type]


def create_llm_client(settings: Settings) -> AbstractLLMClient:
    """Factory: create the right LLM client based on config."""
    if settings.llm_provider == LLMProvider.ollama:
        from app.services.llm.ollama_client import OllamaClient
        return OllamaClient(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout=settings.ollama_timeout_seconds,
            max_retries=settings.ollama_max_retries,
            temperature=settings.ollama_temperature,
            num_ctx=settings.ollama_num_ctx,
        )
    else:
        from app.services.llm.client import AnthropicClient
        return AnthropicClient(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            max_tokens=settings.anthropic_max_tokens,
            timeout=settings.anthropic_timeout_seconds,
            max_retries=settings.anthropic_max_retries,
        )


class LLMExtractionService:
    """
    Calls an LLM to extract structured data from masked document text.

    Input text MUST have been PII-masked before this service is called.
    This is enforced by the pipeline orchestrator (StepPIIMask is critical=True
    and runs before StepLLMExtract).

    Supports both Anthropic (Claude via tool_use) and Ollama (Qwen/Llama via JSON mode).
    """

    def __init__(self, settings: Settings) -> None:
        self._client = create_llm_client(settings)
        self._model_version = self._client.model_name

    async def extract(
        self,
        masked_text: str,
        document_type: DocumentType,
        document_id: str,
    ) -> tuple[ExtractionPayload, dict[str, float], float, str]:
        """
        Run LLM extraction on PII-masked text.

        Returns:
            (extraction_model, confidence_scores, overall_confidence, raw_llm_response_str)

        The raw_llm_response_str should be encrypted before persisting.
        """
        prompt_module = _get_prompt_module(document_type)
        system_prompt: str = prompt_module.SYSTEM_PROMPT  # type: ignore[attr-defined]
        tool_definition: dict = prompt_module.TOOL_DEFINITION  # type: ignore[attr-defined]

        user_message = (
            f"Please extract the structured data from the following financial document.\n\n"
            f"Document type: {document_type.value}\n\n"
            f"--- DOCUMENT TEXT ---\n{masked_text}\n--- END OF DOCUMENT ---"
        )

        logger.info(
            "llm_extraction_started",
            document_id=document_id,
            document_type=document_type.value,
            provider=self._model_version,
            text_length=len(masked_text),
        )

        raw_input = await self._client.call_with_tool(
            system_prompt=system_prompt,
            user_message=user_message,
            tool=tool_definition,
            document_id=document_id,
        )

        # Capture raw response for audit (will be encrypted by caller)
        import json
        raw_response_str = json.dumps(raw_input, default=str)

        extraction, confidence_scores, overall_confidence = parse_llm_output(
            raw_input, document_type
        )

        logger.info(
            "llm_extraction_complete",
            document_id=document_id,
            overall_confidence=round(overall_confidence, 3),
            model_version=self._model_version,
        )

        return extraction, confidence_scores, overall_confidence, raw_response_str

    @property
    def model_version(self) -> str:
        return self._model_version
