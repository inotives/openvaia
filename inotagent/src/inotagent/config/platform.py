"""Load platform-wide config from inotagent/platform.yml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class EmbeddingConfig:
    model: str = ""
    dimensions: int = 1024
    base_url: str = ""
    api_key_env: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> EmbeddingConfig:
        return cls(
            model=data.get("model", ""),
            dimensions=data.get("dimensions", 1024),
            base_url=data.get("base_url", ""),
            api_key_env=data.get("api_key_env", ""),
        )


@dataclass
class PromptGenConfig:
    default_model: str = ""
    fallbacks: list[str] = field(default_factory=list)
    max_tokens: int = 1024

    @classmethod
    def from_dict(cls, data: dict) -> PromptGenConfig:
        return cls(
            default_model=data.get("default_model", ""),
            fallbacks=data.get("fallbacks", []),
            max_tokens=data.get("max_tokens", 1024),
        )


@dataclass
class PlatformConfig:
    default_model: str
    channels: dict = field(default_factory=dict)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    prompt_gen: PromptGenConfig = field(default_factory=PromptGenConfig)

    @classmethod
    def from_dict(cls, data: dict) -> PlatformConfig:
        embedding_data = data.get("embedding", {})
        prompt_gen_data = data.get("prompt_gen", {})
        return cls(
            default_model=data.get("llm", {}).get("default_model", ""),
            channels=data.get("channels", {}),
            embedding=EmbeddingConfig.from_dict(embedding_data),
            prompt_gen=PromptGenConfig.from_dict(prompt_gen_data),
        )


def load_platform_config(path: str | Path) -> PlatformConfig:
    """Load platform.yml and return PlatformConfig."""
    path = Path(path)
    with open(path) as f:
        data = yaml.safe_load(f)
    return PlatformConfig.from_dict(data)
