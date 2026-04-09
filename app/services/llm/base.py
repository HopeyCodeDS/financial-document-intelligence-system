"""
Abstract LLM client interface.

All LLM providers (Anthropic, Ollama, etc.) must satisfy this contract.
The extractor service depends only on this interface, not on a specific provider.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AbstractLLMClient(ABC):
    """Base class for LLM provider clients."""

    @abstractmethod
    async def call_with_tool(
        self,
        system_prompt: str,
        user_message: str,
        tool: dict[str, Any],
        document_id: str,
    ) -> dict[str, Any]:
        """
        Send a structured extraction request to the LLM.

        Args:
            system_prompt: System-level instructions for the model.
            user_message: The document text (PII-masked) with extraction instructions.
            tool: Tool/function schema definition (JSON Schema format).
                  Providers that support tool_use (Claude) use this directly.
                  Providers that don't (Ollama) convert it to a JSON-mode prompt.
            document_id: For logging correlation.

        Returns:
            dict matching the tool's input_schema — validated by Pydantic downstream.

        Raises:
            LLMExtractionError: On API failure or unparseable response.
        """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier string for audit/logging."""
