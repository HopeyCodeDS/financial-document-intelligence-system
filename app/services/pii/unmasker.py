"""
PII unmasker — restores original values into LLM-extracted structured data.
"""
from __future__ import annotations

from typing import Any


def unmask_structured(data: Any, reverse_map: dict[str, str]) -> Any:
    """
    Recursively replace PII tokens with original values.
    """
    if not reverse_map:
        return data

    ordered_tokens = sorted(reverse_map.keys(), key=len, reverse=True)
    return _walk(data, reverse_map, ordered_tokens)


def _walk(node: Any, reverse_map: dict[str, str], ordered_tokens: list[str]) -> Any:
    if isinstance(node, str):
        result = node
        for token in ordered_tokens:
            if token in result:
                result = result.replace(token, reverse_map[token])
        return result
    if isinstance(node, dict):
        return {k: _walk(v, reverse_map, ordered_tokens) for k, v in node.items()}
    if isinstance(node, list):
        return [_walk(item, reverse_map, ordered_tokens) for item in node]
    return node
