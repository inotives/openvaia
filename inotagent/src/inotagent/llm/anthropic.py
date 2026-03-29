"""Anthropic provider — uses official anthropic SDK."""

from __future__ import annotations

import os
from typing import Any

import anthropic

from inotagent.llm.client import LLMMessage, LLMResponse, ToolCall, TokenUsage, strip_think_tags


class AnthropicClient:
    """LLM client for Anthropic models (Claude)."""

    def __init__(self, api_key: str | None = None):
        self._client = anthropic.AsyncAnthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
        )

    async def chat(
        self,
        model: str,
        system: str,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": model,
            "system": system,
            "messages": _convert_messages(messages),
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools

        response = await self._client.messages.create(**kwargs)

        return _parse_response(response)


def _convert_messages(messages: list[LLMMessage]) -> list[dict]:
    """Convert LLMMessage list to Anthropic API format."""
    result: list[dict] = []
    for msg in messages:
        if msg.role == "tool":
            # Tool results go as user messages with tool_result content blocks
            result.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": msg.tool_call_id,
                    "content": msg.content if isinstance(msg.content, str) else str(msg.content),
                }],
            })
        elif msg.role == "assistant" and msg.tool_calls:
            # Assistant message with tool calls
            content: list[dict] = []
            if msg.content:
                content.append({"type": "text", "text": msg.content})
            for tc in msg.tool_calls:
                content.append({
                    "type": "tool_use",
                    "id": tc.id,
                    "name": tc.name,
                    "input": tc.arguments,
                })
            result.append({"role": "assistant", "content": content})
        else:
            result.append({
                "role": msg.role,
                "content": msg.content if isinstance(msg.content, str) else str(msg.content),
            })
    return result


def _parse_response(response: anthropic.types.Message) -> LLMResponse:
    """Parse Anthropic API response into LLMResponse."""
    content_text = ""
    tool_calls: list[ToolCall] = []

    for block in response.content:
        if block.type == "text":
            content_text += block.text
        elif block.type == "tool_use":
            tool_calls.append(ToolCall(
                id=block.id,
                name=block.name,
                arguments=block.input,
            ))

    return LLMResponse(
        content=strip_think_tags(content_text),
        tool_calls=tool_calls,
        usage=TokenUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        ),
        stop_reason=response.stop_reason or "end_turn",
    )
