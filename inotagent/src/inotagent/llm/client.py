"""LLM types and protocol — shared across all providers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol

# Pattern to strip <think>...</think> reasoning blocks from model output.
# Some models (NVIDIA NIM with reasoning enabled) wrap internal reasoning
# in these tags. We strip them so only the final answer is returned.
_THINK_PATTERN = re.compile(r"<think>.*?</think>\s*", re.DOTALL)


def strip_think_tags(text: str) -> str:
    """Remove <think>...</think> blocks from model output."""
    return _THINK_PATTERN.sub("", text).strip()


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class LLMMessage:
    role: str  # "user", "assistant", "tool"
    content: str | list[Any] = ""
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None


@dataclass
class LLMResponse:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)
    stop_reason: str = "end_turn"


class LLMClient(Protocol):
    """Protocol for LLM providers. Implementations must provide chat()."""

    async def chat(
        self,
        model: str,
        system: str,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
    ) -> LLMResponse: ...
