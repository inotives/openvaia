"""Token counting and context window management."""

from __future__ import annotations

import tiktoken

from inotagent.config.models import ModelConfig
from inotagent.llm.client import LLMMessage


# Cache tiktoken encodings
_encoders: dict[str, tiktoken.Encoding] = {}


def _get_encoder(model_id: str) -> tiktoken.Encoding:
    """Get tiktoken encoder, falling back to cl100k_base for non-OpenAI models."""
    if model_id not in _encoders:
        try:
            _encoders[model_id] = tiktoken.encoding_for_model(model_id)
        except KeyError:
            # For non-OpenAI models (NVIDIA, Groq, Anthropic, etc.), use cl100k_base
            # as a reasonable approximation (~10% variance is acceptable for budget math)
            _encoders[model_id] = tiktoken.get_encoding("cl100k_base")
    return _encoders[model_id]


def count_tokens(text: str, model_id: str = "") -> int:
    """Estimate token count for a string."""
    if not text:
        return 0
    enc = _get_encoder(model_id)
    return len(enc.encode(text))


def count_tokens_message(msg: LLMMessage, model_id: str = "") -> int:
    """Estimate token count for a single message (content + role overhead)."""
    tokens = 4  # role + message overhead
    if isinstance(msg.content, str):
        tokens += count_tokens(msg.content, model_id)
    elif isinstance(msg.content, list):
        for block in msg.content:
            if isinstance(block, dict) and "text" in block:
                tokens += count_tokens(block["text"], model_id)
            elif isinstance(block, str):
                tokens += count_tokens(block, model_id)
    if msg.tool_calls:
        for tc in msg.tool_calls:
            tokens += count_tokens(tc.name, model_id)
            tokens += count_tokens(str(tc.arguments), model_id)
    return tokens


def estimate_tools_tokens(tools: list[dict] | None, model_id: str = "") -> int:
    """Estimate token cost of tool definitions."""
    if not tools:
        return 0
    import json
    return count_tokens(json.dumps(tools), model_id)


def build_context(
    system: str,
    history: list[LLMMessage],
    tools: list[dict] | None,
    model_config: ModelConfig,
    reserve_output: int | None = None,
) -> list[LLMMessage]:
    """Truncate history to fit within context window.

    Strategy:
    1. System prompt + tool defs are always included (fixed cost)
    2. Most recent messages are kept (sliding window)
    3. Oldest messages are dropped first
    4. Reserve tokens for model output
    """
    max_context = model_config.context_window
    output_reserve = reserve_output or model_config.max_tokens
    available = max_context - output_reserve

    fixed_cost = count_tokens(system, model_config.id) + estimate_tools_tokens(tools, model_config.id)
    budget = available - fixed_cost

    if budget <= 0:
        return []

    # Keep messages from newest to oldest until budget exhausted
    kept: list[LLMMessage] = []
    used = 0
    for msg in reversed(history):
        msg_tokens = count_tokens_message(msg, model_config.id)
        if used + msg_tokens > budget:
            break
        kept.insert(0, msg)
        used += msg_tokens

    return kept
