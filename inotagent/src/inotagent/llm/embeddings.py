"""Embedding client for semantic memory search via NVIDIA NIM (OpenAI-compatible)."""

from __future__ import annotations

import logging
import os

import httpx

from inotagent.config.platform import EmbeddingConfig

logger = logging.getLogger(__name__)

# Module-level singleton — initialized once at startup
_client: EmbeddingClient | None = None


class EmbeddingClient:
    """Generate text embeddings via OpenAI-compatible embedding API."""

    def __init__(self, config: EmbeddingConfig):
        self._model = config.model
        self._dimensions = config.dimensions
        self._base_url = config.base_url.rstrip("/")
        api_key = os.environ.get(config.api_key_env) if config.api_key_env else ""
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def embed(self, texts: list[str], input_type: str = "passage") -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of strings to embed.
            input_type: "passage" for storing, "query" for searching.

        Returns:
            List of embedding vectors (each a list of floats).
        """
        payload = {
            "input": texts,
            "model": self._model,
            "input_type": input_type,
            "encoding_format": "float",
            "truncate": "END",
            "dimensions": self._dimensions,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._base_url}/embeddings",
                headers=self._headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        # Sort by index to ensure correct order
        embeddings = sorted(data["data"], key=lambda x: x["index"])
        return [e["embedding"] for e in embeddings]

    async def embed_one(self, text: str, input_type: str = "passage") -> list[float]:
        """Generate embedding for a single text."""
        results = await self.embed([text], input_type=input_type)
        return results[0]


def init_embedding_client(config: EmbeddingConfig) -> bool:
    """Initialize the global embedding client. Returns True if successful."""
    global _client
    if not config.model or not config.base_url:
        logger.info("Embedding not configured, semantic memory search disabled")
        return False

    api_key_env = config.api_key_env
    if api_key_env and not os.environ.get(api_key_env):
        logger.warning(f"Embedding configured but {api_key_env} not set, skipping")
        return False

    _client = EmbeddingClient(config)
    logger.info(f"Embedding client initialized: {config.model} ({config.dimensions}d)")
    return True


def get_embedding_client() -> EmbeddingClient | None:
    """Get the global embedding client, or None if not initialized."""
    return _client
