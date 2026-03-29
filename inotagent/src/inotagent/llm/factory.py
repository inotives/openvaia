"""Create LLM clients from model config."""

from __future__ import annotations

import logging
import os

from inotagent.config.models import ModelConfig
from inotagent.llm.anthropic import AnthropicClient
from inotagent.llm.client import LLMResponse
from inotagent.llm.openai_compat import OpenAICompatClient

logger = logging.getLogger(__name__)

# Providers that use the Anthropic SDK
ANTHROPIC_PROVIDERS = {"anthropic"}

# Providers that use OpenAI-compatible API
OPENAI_COMPAT_PROVIDERS = {"nvidia", "groq", "openai", "ollama", "google"}


def create_client(model_config: ModelConfig) -> AnthropicClient | OpenAICompatClient:
    """Create the appropriate LLM client for a model's provider."""
    if model_config.provider in ANTHROPIC_PROVIDERS:
        api_key = os.environ.get(model_config.api_key_env) if model_config.api_key_env else None
        return AnthropicClient(api_key=api_key)

    if model_config.provider in OPENAI_COMPAT_PROVIDERS:
        if not model_config.base_url:
            raise ValueError(f"Model '{model_config.id}' (provider={model_config.provider}) requires base_url")
        return OpenAICompatClient(
            base_url=model_config.base_url,
            api_key_env=model_config.api_key_env,
        )

    raise ValueError(f"Unknown provider '{model_config.provider}' for model '{model_config.id}'")


class RateLimitError(Exception):
    pass


class AllModelsFailed(Exception):
    pass


async def chat_with_fallback(
    models: dict[str, ModelConfig],
    model_id: str,
    fallbacks: list[str],
    **kwargs,
) -> LLMResponse:
    """Try primary model, then fallbacks on failure."""
    chain = [model_id] + fallbacks
    last_error: Exception | None = None

    for mid in chain:
        if mid not in models:
            logger.warning(f"Fallback model '{mid}' not in registry, skipping")
            continue
        try:
            client = create_client(models[mid])
            return await client.chat(model=models[mid].model, **kwargs)
        except Exception as e:
            logger.warning(f"Model {mid} failed: {e}, trying next")
            last_error = e

    raise AllModelsFailed(f"All models failed: {chain}. Last error: {last_error}")
