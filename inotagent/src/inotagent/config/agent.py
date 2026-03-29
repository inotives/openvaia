"""Load agent config from agent.yml + workspace files."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from inotagent.config.models import ModelConfig
from inotagent.config.platform import PlatformConfig

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    name: str
    model_id: str
    fallbacks: list[str] = field(default_factory=list)
    system_prompt: str = ""
    channels: dict = field(default_factory=dict)
    parallel: bool = False
    mission_tags: list[str] = field(default_factory=list)
    _agent_dir: Path | None = field(default=None, repr=False)
    _skill_content: str = field(default="", repr=False)
    _skill_names: list[str] = field(default_factory=list, repr=False)
    _skill_ids: list[int] = field(default_factory=list, repr=False)

    @property
    def system_prompt_with_skills(self) -> str:
        """System prompt with resolved skills appended."""
        if self._skill_content:
            return self.system_prompt + "\n\n" + self._skill_content
        return self.system_prompt

    async def refresh_from_db(self, models: dict[str, ModelConfig]) -> None:
        """Reload config from agent_configs DB table, overriding YAML values.

        Only overrides model_id/fallbacks/mission_tags/parallel.
        Channels stay from agent.yml (infrastructure config).
        """
        from inotagent.db.agent_configs import load_agent_configs

        db_configs = await load_agent_configs(self.name)
        if not db_configs:
            logger.info(f"No DB configs for '{self.name}', using YAML values")
            return

        changed = []

        # Model
        if "model" in db_configs and db_configs["model"]:
            new_model = db_configs["model"]
            if new_model in models and new_model != self.model_id:
                self.model_id = new_model
                changed.append(f"model={new_model}")
                # Rebuild system prompt with new model info
                if self._agent_dir:
                    self.system_prompt = _build_system_prompt(self._agent_dir, models[new_model])
            elif new_model not in models:
                logger.warning(f"DB model '{new_model}' not in registry, keeping '{self.model_id}'")

        # Fallbacks
        if "fallbacks" in db_configs:
            try:
                new_fallbacks = json.loads(db_configs["fallbacks"])
                if isinstance(new_fallbacks, list):
                    valid = [f for f in new_fallbacks if f in models]
                    if valid != self.fallbacks:
                        self.fallbacks = valid
                        changed.append(f"fallbacks={valid}")
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Invalid fallbacks JSON in DB: {db_configs['fallbacks']}")

        # Mission tags
        if "mission_tags" in db_configs:
            try:
                new_tags = json.loads(db_configs["mission_tags"])
                if isinstance(new_tags, list) and new_tags != self.mission_tags:
                    self.mission_tags = new_tags
                    changed.append(f"mission_tags={new_tags}")
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Invalid mission_tags JSON in DB: {db_configs['mission_tags']}")

        # Parallel
        if "parallel" in db_configs:
            new_parallel = db_configs["parallel"].lower() in ("true", "1", "yes")
            if new_parallel != self.parallel:
                self.parallel = new_parallel
                changed.append(f"parallel={new_parallel}")

        if changed:
            logger.info(f"DB config overrides for '{self.name}': {', '.join(changed)}")
        else:
            logger.info(f"DB configs loaded for '{self.name}', no changes from YAML")

    async def refresh_skills(self) -> None:
        """Reload skills from DB and update cached content."""
        from inotagent.db.skills import load_agent_skills
        skills = await load_agent_skills(self.name)
        self._skill_ids = [s["id"] for s in skills]
        self._skill_names = [s["name"] for s in skills]
        if skills:
            self._skill_content = "\n\n".join(s["content"] for s in skills)
        else:
            self._skill_content = ""


def load_agent_config(
    agent_dir: str | Path,
    models: dict[str, ModelConfig],
    platform: PlatformConfig,
) -> AgentConfig:
    """Load agent.yml + AGENTS.md + TOOLS.md into AgentConfig.

    System prompt = AGENTS.md (persona, role, workflows)
                  + TOOLS.md (behavioral rules only, ~200-300 tokens)

    MEMORY.md is NOT loaded into system prompt. Memory is stored in
    Postgres and accessed on-demand via the memory_search tool.

    Tool schemas are NOT in the system prompt — they go in
    the LLM API `tools` parameter (function calling). No duplication.
    """
    agent_dir = Path(agent_dir)

    # Agent name from env or directory name
    name = os.environ.get("AGENT_NAME", agent_dir.name)

    # Load agent.yml
    agent_yml = agent_dir / "agent.yml"
    agent_data: dict = {}
    if agent_yml.exists():
        with open(agent_yml) as f:
            agent_data = yaml.safe_load(f) or {}

    # Resolve model: agent.yml → platform.yml default → first in registry
    model_id = agent_data.get("model") or platform.default_model or next(iter(models), "")
    if model_id not in models:
        available = list(models.keys())[:5]
        raise ValueError(f"Model '{model_id}' not found in registry. Available: {available}")

    fallbacks = agent_data.get("fallbacks", [])
    # Filter out fallbacks not in registry
    fallbacks = [f for f in fallbacks if f in models]

    parallel = agent_data.get("parallel", False)
    channels = agent_data.get("channels", {})
    mission_tags = agent_data.get("mission_tags", [])

    # Build system prompt from workspace files + model info
    model_config = models[model_id]
    system_prompt = _build_system_prompt(agent_dir, model_config)

    return AgentConfig(
        name=name,
        model_id=model_id,
        fallbacks=fallbacks,
        system_prompt=system_prompt,
        channels=channels,
        parallel=parallel,
        mission_tags=mission_tags,
        _agent_dir=agent_dir,
    )


def _build_system_prompt(agent_dir: Path, model_config: ModelConfig | None = None) -> str:
    """Build system prompt from AGENTS.md + TOOLS.md + model info."""
    parts: list[str] = []

    agents_md = agent_dir / "AGENTS.md"
    if agents_md.exists():
        parts.append(agents_md.read_text().strip())

    tools_md = agent_dir / "TOOLS.md"
    if tools_md.exists():
        parts.append(tools_md.read_text().strip())

    if model_config:
        parts.append(
            f"## Runtime\n"
            f"- Model: {model_config.model} (id: {model_config.id}, provider: {model_config.provider})\n"
            f"- Context window: {model_config.context_window} tokens\n"
            f"- Max output: {model_config.max_tokens} tokens"
        )

    return "\n\n".join(parts)
