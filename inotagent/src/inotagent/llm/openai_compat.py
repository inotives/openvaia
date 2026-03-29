"""OpenAI-compatible provider — NVIDIA NIM, Groq, Ollama, OpenAI, Google via httpx."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from inotagent.llm.client import LLMMessage, LLMResponse, ToolCall, TokenUsage, strip_think_tags


class OpenAICompatClient:
    """LLM client for OpenAI-compatible APIs (NVIDIA, Groq, Ollama, OpenAI)."""

    def __init__(self, base_url: str, api_key: str | None = None, api_key_env: str | None = None):
        resolved_key = api_key or (os.environ.get(api_key_env) if api_key_env else None) or ""
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {resolved_key}",
            "Content-Type": "application/json",
        }

    async def chat(
        self,
        model: str,
        system: str,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        openai_messages = _convert_messages(system, messages)

        payload: dict[str, Any] = {
            "model": model,
            "messages": openai_messages,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = _convert_tools(tools)

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers=self._headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        return _parse_response(data)


def _convert_messages(system: str, messages: list[LLMMessage]) -> list[dict]:
    """Convert LLMMessage list to OpenAI chat format with system message."""
    result: list[dict] = [{"role": "system", "content": system}]

    for msg in messages:
        if msg.role == "tool":
            result.append({
                "role": "tool",
                "tool_call_id": msg.tool_call_id,
                "content": msg.content if isinstance(msg.content, str) else str(msg.content),
            })
        elif msg.role == "assistant" and msg.tool_calls:
            entry: dict[str, Any] = {"role": "assistant"}
            if msg.content:
                entry["content"] = msg.content
            else:
                entry["content"] = None
            entry["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments),
                    },
                }
                for tc in msg.tool_calls
            ]
            result.append(entry)
        else:
            result.append({
                "role": msg.role,
                "content": msg.content if isinstance(msg.content, str) else str(msg.content),
            })

    return result


def _convert_tools(anthropic_tools: list[dict]) -> list[dict]:
    """Convert Anthropic tool format to OpenAI function calling format.

    Anthropic format:
        {"name": "...", "description": "...", "input_schema": {...}}
    OpenAI format:
        {"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}
    """
    openai_tools: list[dict] = []
    for tool in anthropic_tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {}),
            },
        })
    return openai_tools


def _parse_response(data: dict) -> LLMResponse:
    """Parse OpenAI-format response into LLMResponse."""
    choice = data["choices"][0]
    message = choice["message"]

    content = strip_think_tags(message.get("content") or "")
    tool_calls: list[ToolCall] = []

    if message.get("tool_calls"):
        for tc in message["tool_calls"]:
            func = tc["function"]
            arguments = func.get("arguments", "{}")
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {"raw": arguments}

            tool_calls.append(ToolCall(
                id=tc["id"],
                name=func["name"],
                arguments=arguments,
            ))

    usage_data = data.get("usage", {})
    usage = TokenUsage(
        input_tokens=usage_data.get("prompt_tokens", 0),
        output_tokens=usage_data.get("completion_tokens", 0),
    )

    finish_reason = choice.get("finish_reason", "stop")
    stop_reason = "tool_use" if finish_reason == "tool_calls" else "end_turn"

    return LLMResponse(
        content=content,
        tool_calls=tool_calls,
        usage=usage,
        stop_reason=stop_reason,
    )
