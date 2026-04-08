"""
Claude Client — async wrapper around the Anthropic SDK for streaming chat.

Uses prompt caching (cache_control) on the stable sections of the system
prompt (Sections 1–4). Section 5 (few-shot examples) is dynamic and
not cached.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import anthropic

from app.config import settings

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


def _split_prompt(system_prompt: str) -> tuple[str, str]:
    """
    Split the system prompt into a stable part (Sections 1–4) and a
    dynamic part (Section 5 — few-shot examples).
    """
    marker = "## [5]"
    idx = system_prompt.find(marker)
    if idx == -1:
        return system_prompt, ""
    return system_prompt[:idx].strip(), system_prompt[idx:].strip()


def _build_system_blocks(system_prompt: str) -> list[dict[str, Any]]:
    """
    Build the `system` parameter for the Messages API.
    The stable part is marked with cache_control so Anthropic can cache it.
    """
    stable, dynamic = _split_prompt(system_prompt)
    blocks: list[dict[str, Any]] = []

    if stable:
        blocks.append({
            "type": "text",
            "text": stable,
            "cache_control": {"type": "ephemeral"},
        })
    if dynamic:
        blocks.append({
            "type": "text",
            "text": dynamic,
        })
    return blocks


async def stream_chat(
    system_prompt: str,
    history: list[dict[str, str]],
    user_message: str,
) -> AsyncGenerator[str, None]:
    """
    Stream a chat response using the Claude API.

    Args:
        system_prompt: Full system prompt for the persona.
        history: List of previous messages [{"role": ..., "content": ...}].
        user_message: The current user input.

    Yields:
        Text chunks as they arrive from the API.
    """
    client = _get_client()
    system_blocks = _build_system_blocks(system_prompt)

    messages = list(history) + [{"role": "user", "content": user_message}]

    async with client.messages.stream(
        model=settings.claude_model,
        max_tokens=1024,
        system=system_blocks,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            yield text


async def complete_chat(
    system_prompt: str,
    history: list[dict[str, str]],
    user_message: str,
) -> str:
    """Non-streaming version — returns the full response as a string."""
    chunks = []
    async for chunk in stream_chat(system_prompt, history, user_message):
        chunks.append(chunk)
    return "".join(chunks)
