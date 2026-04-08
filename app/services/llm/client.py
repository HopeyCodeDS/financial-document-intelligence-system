"""
Async Anthropic client wrapper with retry logic and rate-limit handling.

Wraps anthropic.AsyncAnthropic with:
- Tenacity retry on transient errors (rate limit, server errors)
- Structured logging of every API call
- Timeout enforcement
"""
from __future__ import annotations

import time
from typing import Any

import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)
import structlog

from app.core.exceptions import LLMExtractionError, LLMRateLimitError
from app.core.logging import get_logger
from app.services.llm.base import AbstractLLMClient

logger = get_logger(__name__)


def _is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, (anthropic.RateLimitError, anthropic.InternalServerError))


class AnthropicClient(AbstractLLMClient):
    """Thin async wrapper around anthropic.AsyncAnthropic with retry + logging."""

    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int,
        timeout: int,
        max_retries: int,
    ) -> None:
        self._client = anthropic.AsyncAnthropic(
            api_key=api_key,
            timeout=float(timeout),
            max_retries=0,  # We handle retries ourselves via tenacity
        )
        self._model = model
        self._max_tokens = max_tokens
        self._max_retries = max_retries

    async def call_with_tool(
        self,
        system_prompt: str,
        user_message: str,
        tool: dict[str, Any],
        document_id: str,
    ) -> dict[str, Any]:
        """
        Call Claude with a tool definition and extract the tool_use result.

        Forces structured output by providing a single tool and setting
        tool_choice to that tool — Claude must return exactly one tool call.

        Returns the tool input dict (validated downstream by Pydantic).
        Raises LLMExtractionError on API failure or unexpected response format.
        """
        start = time.monotonic()

        @retry(
            retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.InternalServerError)),
            stop=stop_after_attempt(self._max_retries + 1),
            wait=wait_exponential(multiplier=1, min=4, max=60),
            reraise=True,
        )
        async def _attempt() -> anthropic.types.Message:
            return await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system_prompt,
                tools=[tool],
                tool_choice={"type": "tool", "name": tool["name"]},
                messages=[{"role": "user", "content": user_message}],
            )

        try:
            response = await _attempt()
        except anthropic.RateLimitError as exc:
            raise LLMRateLimitError(f"Anthropic rate limit exceeded: {exc}") from exc
        except anthropic.APIError as exc:
            raise LLMExtractionError(f"Anthropic API error: {exc}") from exc

        duration_ms = int((time.monotonic() - start) * 1000)

        logger.info(
            "llm_call_complete",
            document_id=document_id,
            model=self._model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            duration_ms=duration_ms,
        )

        # Extract tool_use block
        tool_use_block = next(
            (block for block in response.content if block.type == "tool_use"),
            None,
        )
        if tool_use_block is None:
            raise LLMExtractionError(
                f"Claude did not return a tool_use block. "
                f"Stop reason: {response.stop_reason}. Content: {response.content!r}"
            )

        return tool_use_block.input  # type: ignore[return-value]

    @property
    def model_name(self) -> str:
        return self._model
