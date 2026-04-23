"""
Ollama client for local LLM extraction (Qwen, Llama, etc.).

Since Ollama does not support tool_use, this client:
1. Converts the tool schema into a JSON-mode prompt with explicit schema
2. Requests JSON output via Ollama's format="json" parameter
3. Parses the raw JSON response, handling common formatting issues
4. Returns the same dict structure as AnthropicClient for downstream Pydantic validation

Compatible models:
- qwen2.5:7b, qwen2.5:14b, qwen2.5:32b, qwen2.5:72b
- llama3.1:8b, llama3.1:70b
- Any Ollama model that supports JSON output mode
"""
from __future__ import annotations

import json
import re
import time
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.exceptions import LLMExtractionError
from app.core.logging import get_logger
from app.services.llm.base import AbstractLLMClient

logger = get_logger(__name__)


class OllamaClient(AbstractLLMClient):
    """
    Async Ollama client that bridges the tool_use interface to JSON-mode prompting.

    Ollama exposes a REST API at http://localhost:11434 by default.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:14b",
        timeout: int = 120,
        max_retries: int = 2,
        temperature: float = 0.0,
        num_ctx: int = 8192,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries
        self._temperature = temperature
        self._num_ctx = num_ctx

    @property
    def model_name(self) -> str:
        return f"ollama/{self._model}"

    async def call_with_tool(
        self,
        system_prompt: str,
        user_message: str,
        tool: dict[str, Any],
        document_id: str,
    ) -> dict[str, Any]:
        """
        Convert tool schema to a JSON-mode prompt and call Ollama.

        The tool's input_schema is embedded directly in the prompt so the model
        knows exactly what JSON structure to produce. We use format="json" to
        enforce valid JSON output from Ollama.
        """
        json_schema = json.dumps(tool["input_schema"], indent=2)

        # Build a system prompt that instructs the model to output strict JSON
        enhanced_system = (
            f"{system_prompt}\n\n"
            f"CRITICAL INSTRUCTION: You must respond with ONLY a valid JSON object.\n"
            f"Do not include any text, explanation, or markdown — just the raw JSON.\n\n"
            f"The JSON must conform exactly to this schema:\n"
            f"```json\n{json_schema}\n```\n\n"
            f"Rules:\n"
            f"- Every field listed in 'required' must be present\n"
            f"- If you cannot extract a field, set value to null and confidence to 0.0\n"
            f"- Confidence must be a number between 0.0 and 1.0\n"
            f"- Do NOT add fields that are not in the schema"
        )

        start = time.monotonic()

        @retry(
            retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
            stop=stop_after_attempt(self._max_retries + 1),
            wait=wait_exponential(multiplier=1, min=2, max=30),
            reraise=True,
        )
        async def _attempt() -> dict[str, Any]:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/api/chat",
                    json={
                        "model": self._model,
                        "messages": [
                            {"role": "system", "content": enhanced_system},
                            {"role": "user", "content": user_message},
                        ],
                        "format": "json",
                        "stream": False,
                        "options": {
                            "temperature": self._temperature,
                            "num_ctx": self._num_ctx,
                            "num_predict": 4096,
                        },
                    },
                )
                response.raise_for_status()
                return response.json()

        try:
            result = await _attempt()
        except httpx.ConnectError as exc:
            raise LLMExtractionError(
                f"Cannot connect to Ollama at {self._base_url}. "
                f"Is Ollama running? Error: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMExtractionError(
                f"Ollama request timed out after {self._timeout}s: {exc}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise LLMExtractionError(
                f"Ollama API error {exc.response.status_code}: {exc.response.text}"
            ) from exc

        duration_ms = int((time.monotonic() - start) * 1000)

        # Extract content from Ollama response
        raw_content = result.get("message", {}).get("content", "")

        logger.info(
            "llm_call_complete",
            document_id=document_id,
            model=self._model,
            provider="ollama",
            duration_ms=duration_ms,
            eval_count=result.get("eval_count"),
            prompt_eval_count=result.get("prompt_eval_count"),
        )

        # Parse JSON from the response
        parsed = self._parse_json_response(raw_content, document_id)
        return parsed

    def _parse_json_response(self, raw: str, document_id: str) -> dict[str, Any]:
        """
        Parse JSON from Ollama response, handling common formatting issues.

        Local models sometimes wrap JSON in markdown fences or add explanatory text.
        We handle these cases gracefully.
        """
        text = raw.strip()

        # Try direct parse first (ideal case)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code fences
        fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        if fence_match:
            try:
                return json.loads(fence_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try finding the first { ... } block
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        raise LLMExtractionError(
            f"Ollama model returned non-JSON response for document {document_id}. "
            f"Raw response (first 500 chars): {text[:500]}"
        )
