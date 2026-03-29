"""Load model registry from inotagent/models.yml."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class ModelConfig:
    id: str
    provider: str
    model: str
    api_key_env: str | None
    base_url: str | None
    context_window: int
    max_tokens: int

    @classmethod
    def from_dict(cls, data: dict) -> ModelConfig:
        return cls(
            id=data["id"],
            provider=data["provider"],
            model=data["model"],
            api_key_env=data.get("api_key_env"),
            base_url=data.get("base_url"),
            context_window=data["context_window"],
            max_tokens=data["max_tokens"],
        )


def load_models(path: str | Path) -> dict[str, ModelConfig]:
    """Load models.yml and return dict keyed by model id."""
    path = Path(path)
    with open(path) as f:
        data = yaml.safe_load(f)

    models: dict[str, ModelConfig] = {}
    for entry in data.get("models", []):
        config = ModelConfig.from_dict(entry)
        models[config.id] = config
    return models
