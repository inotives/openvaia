"""Tests for config loading — models, platform, agent."""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest

from inotagent.config.agent import AgentConfig, load_agent_config, _build_system_prompt
from inotagent.config.models import ModelConfig, load_models
from inotagent.config.platform import PlatformConfig, load_platform_config


# --- Fixtures ---


@pytest.fixture
def models_yml(tmp_path: Path) -> Path:
    """Create a test models.yml."""
    p = tmp_path / "models.yml"
    p.write_text(textwrap.dedent("""\
        models:
          - id: test-model-1
            provider: nvidia
            model: test/model-1
            api_key_env: TEST_API_KEY
            base_url: https://api.test.com/v1
            context_window: 128000
            max_tokens: 4096

          - id: test-model-2
            provider: anthropic
            model: claude-test
            api_key_env: ANTHROPIC_API_KEY
            context_window: 200000
            max_tokens: 8192

          - id: test-model-local
            provider: ollama
            model: llama3
            api_key_env: null
            base_url: http://localhost:11434/v1
            context_window: 8192
            max_tokens: 4096
    """))
    return p


@pytest.fixture
def platform_yml(tmp_path: Path) -> Path:
    """Create a test platform.yml."""
    p = tmp_path / "platform.yml"
    p.write_text(textwrap.dedent("""\
        llm:
          default_model: test-model-1

        channels:
          defaults:
            groupPolicy: allowlist
          discord:
            enabled: false
            token_env: DISCORD_BOT_TOKEN
    """))
    return p


@pytest.fixture
def agent_dir(tmp_path: Path) -> Path:
    """Create a test agent directory with agent.yml, AGENTS.md, TOOLS.md."""
    agent = tmp_path / "agents" / "testbot"
    agent.mkdir(parents=True)

    (agent / "agent.yml").write_text(textwrap.dedent("""\
        model: test-model-1
        fallbacks:
          - test-model-2
        channels:
          discord:
            enabled: true
            allowFrom: ["123"]
    """))

    (agent / "AGENTS.md").write_text("# TestBot\nYou are a test agent.\n")
    (agent / "TOOLS.md").write_text("## Rules\nAlways test your code.\n")

    return agent


@pytest.fixture
def models(models_yml: Path) -> dict[str, ModelConfig]:
    return load_models(models_yml)


@pytest.fixture
def platform(platform_yml: Path) -> PlatformConfig:
    return load_platform_config(platform_yml)


# --- Model config tests ---


class TestLoadModels:
    def test_load_all_models(self, models: dict[str, ModelConfig]):
        assert len(models) == 3
        assert "test-model-1" in models
        assert "test-model-2" in models
        assert "test-model-local" in models

    def test_model_fields(self, models: dict[str, ModelConfig]):
        m = models["test-model-1"]
        assert m.id == "test-model-1"
        assert m.provider == "nvidia"
        assert m.model == "test/model-1"
        assert m.api_key_env == "TEST_API_KEY"
        assert m.base_url == "https://api.test.com/v1"
        assert m.context_window == 128000
        assert m.max_tokens == 4096

    def test_anthropic_model_no_base_url(self, models: dict[str, ModelConfig]):
        m = models["test-model-2"]
        assert m.provider == "anthropic"
        assert m.base_url is None

    def test_null_api_key(self, models: dict[str, ModelConfig]):
        m = models["test-model-local"]
        assert m.api_key_env is None

    def test_empty_file(self, tmp_path: Path):
        p = tmp_path / "empty.yml"
        p.write_text("models: []\n")
        models = load_models(p)
        assert models == {}

    def test_missing_file(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_models(tmp_path / "nonexistent.yml")

    def test_load_real_models_yml(self):
        """Load the actual inotagent/models.yml to verify compatibility."""
        # inotagent/tests/ → inotagent/
        real_path = Path(__file__).resolve().parent.parent / "models.yml"
        if not real_path.exists():
            pytest.skip("inotagent/models.yml not found (running outside repo)")
        models = load_models(real_path)
        assert len(models) > 0
        # Verify known models exist
        assert "nvidia-glm5" in models
        assert models["nvidia-glm5"].provider == "nvidia"


# --- Platform config tests ---


class TestLoadPlatformConfig:
    def test_default_model(self, platform: PlatformConfig):
        assert platform.default_model == "test-model-1"

    def test_channels(self, platform: PlatformConfig):
        assert "discord" in platform.channels
        assert platform.channels["discord"]["token_env"] == "DISCORD_BOT_TOKEN"

    def test_embedding_defaults_when_missing(self, platform: PlatformConfig):
        """Embedding config defaults when not in platform.yml."""
        assert platform.embedding.model == ""
        assert platform.embedding.dimensions == 1024

    def test_prompt_gen_defaults_when_missing(self, platform: PlatformConfig):
        """Prompt gen config defaults when not in platform.yml."""
        assert platform.prompt_gen.default_model == ""
        assert platform.prompt_gen.fallbacks == []
        assert platform.prompt_gen.max_tokens == 1024

    def test_prompt_gen_from_yml(self, tmp_path: Path):
        """Prompt gen config loads from platform.yml."""
        p = tmp_path / "platform.yml"
        p.write_text(textwrap.dedent("""\
            llm:
              default_model: test-model-1
            prompt_gen:
              default_model: groq-llama-3.3-70b
              fallbacks:
                - nvidia-minimax-2.1
              max_tokens: 512
        """))
        platform = load_platform_config(p)
        assert platform.prompt_gen.default_model == "groq-llama-3.3-70b"
        assert platform.prompt_gen.fallbacks == ["nvidia-minimax-2.1"]
        assert platform.prompt_gen.max_tokens == 512

    def test_embedding_from_yml(self, tmp_path: Path):
        """Embedding config loads from platform.yml."""
        p = tmp_path / "platform.yml"
        p.write_text(textwrap.dedent("""\
            llm:
              default_model: test-model-1
            embedding:
              model: nvidia/llama-nemotron-embed-1b-v2
              dimensions: 1024
              base_url: https://integrate.api.nvidia.com/v1
              api_key_env: NVIDIA_API_KEY
        """))
        platform = load_platform_config(p)
        assert platform.embedding.model == "nvidia/llama-nemotron-embed-1b-v2"
        assert platform.embedding.dimensions == 1024
        assert platform.embedding.base_url == "https://integrate.api.nvidia.com/v1"
        assert platform.embedding.api_key_env == "NVIDIA_API_KEY"

    def test_load_real_platform_yml(self):
        """Load actual inotagent/platform.yml."""
        real_path = Path(__file__).resolve().parent.parent / "platform.yml"
        if not real_path.exists():
            pytest.skip("inotagent/platform.yml not found (running outside repo)")
        platform = load_platform_config(real_path)
        assert platform.default_model != ""
        assert platform.embedding.model == "nvidia/llama-nemotron-embed-1b-v2"


# --- Agent config tests ---


class TestLoadAgentConfig:
    def test_basic_load(self, agent_dir: Path, models: dict, platform: PlatformConfig):
        config = load_agent_config(agent_dir, models, platform)
        assert config.name == "testbot"
        assert config.model_id == "test-model-1"
        assert config.fallbacks == ["test-model-2"]
        assert config.parallel is False

    def test_system_prompt_combines_agents_and_tools(self, agent_dir: Path, models: dict, platform: PlatformConfig):
        config = load_agent_config(agent_dir, models, platform)
        assert "# TestBot" in config.system_prompt
        assert "You are a test agent." in config.system_prompt
        assert "## Rules" in config.system_prompt
        assert "Always test your code." in config.system_prompt

    def test_system_prompt_includes_model_info(self, agent_dir: Path, models: dict, platform: PlatformConfig):
        config = load_agent_config(agent_dir, models, platform)
        assert "## Runtime" in config.system_prompt
        assert "test/model-1" in config.system_prompt
        assert "test-model-1" in config.system_prompt
        assert "nvidia" in config.system_prompt

    def test_channels_from_agent_yml(self, agent_dir: Path, models: dict, platform: PlatformConfig):
        config = load_agent_config(agent_dir, models, platform)
        assert config.channels["discord"]["enabled"] is True
        assert config.channels["discord"]["allowFrom"] == ["123"]

    def test_agent_name_from_env(self, agent_dir: Path, models: dict, platform: PlatformConfig, monkeypatch):
        monkeypatch.setenv("AGENT_NAME", "custom-name")
        config = load_agent_config(agent_dir, models, platform)
        assert config.name == "custom-name"

    def test_model_fallback_to_platform_default(self, tmp_path: Path, models: dict, platform: PlatformConfig):
        """When agent.yml has no model, use platform default."""
        agent = tmp_path / "agents" / "nomodel"
        agent.mkdir(parents=True)
        (agent / "agent.yml").write_text("fallbacks: []\n")
        config = load_agent_config(agent, models, platform)
        assert config.model_id == "test-model-1"  # platform default

    def test_model_fallback_to_first_in_registry(self, tmp_path: Path, models: dict):
        """When no platform default, use first model in registry."""
        platform = PlatformConfig(default_model="")
        agent = tmp_path / "agents" / "nomodel"
        agent.mkdir(parents=True)
        (agent / "agent.yml").write_text("{}\n")
        config = load_agent_config(agent, models, platform)
        assert config.model_id == "test-model-1"

    def test_invalid_model_raises(self, tmp_path: Path, models: dict, platform: PlatformConfig):
        agent = tmp_path / "agents" / "badmodel"
        agent.mkdir(parents=True)
        (agent / "agent.yml").write_text("model: nonexistent-model\n")
        with pytest.raises(ValueError, match="not found in registry"):
            load_agent_config(agent, models, platform)

    def test_invalid_fallback_filtered(self, tmp_path: Path, models: dict, platform: PlatformConfig):
        """Fallback models not in registry are silently filtered out."""
        agent = tmp_path / "agents" / "badfallback"
        agent.mkdir(parents=True)
        (agent / "agent.yml").write_text(textwrap.dedent("""\
            model: test-model-1
            fallbacks:
              - test-model-2
              - nonexistent-model
        """))
        config = load_agent_config(agent, models, platform)
        assert config.fallbacks == ["test-model-2"]

    def test_parallel_flag(self, tmp_path: Path, models: dict, platform: PlatformConfig):
        agent = tmp_path / "agents" / "parallel"
        agent.mkdir(parents=True)
        (agent / "agent.yml").write_text("model: test-model-1\nparallel: true\n")
        config = load_agent_config(agent, models, platform)
        assert config.parallel is True

    def test_missing_agents_md(self, tmp_path: Path, models: dict, platform: PlatformConfig):
        """Agent works even without AGENTS.md/TOOLS.md (still has runtime info)."""
        agent = tmp_path / "agents" / "minimal"
        agent.mkdir(parents=True)
        (agent / "agent.yml").write_text("model: test-model-1\n")
        config = load_agent_config(agent, models, platform)
        # No AGENTS.md/TOOLS.md, but runtime info is still injected
        assert "## Runtime" in config.system_prompt
        assert "# " not in config.system_prompt.split("## Runtime")[0]  # no markdown before runtime

    def test_no_agent_yml(self, tmp_path: Path, models: dict, platform: PlatformConfig):
        """Agent works without agent.yml (uses defaults)."""
        agent = tmp_path / "agents" / "noyml"
        agent.mkdir(parents=True)
        config = load_agent_config(agent, models, platform)
        assert config.model_id == platform.default_model


class TestBuildSystemPrompt:
    def test_only_agents_md(self, tmp_path: Path):
        (tmp_path / "AGENTS.md").write_text("# Agent\nHello\n")
        prompt = _build_system_prompt(tmp_path)
        assert prompt == "# Agent\nHello"

    def test_both_files(self, tmp_path: Path):
        (tmp_path / "AGENTS.md").write_text("# Agent\nPersona\n")
        (tmp_path / "TOOLS.md").write_text("# Tools\nRules\n")
        prompt = _build_system_prompt(tmp_path)
        assert "# Agent\nPersona" in prompt
        assert "# Tools\nRules" in prompt
        # Separated by double newline
        assert "\n\n" in prompt

    def test_empty_dir(self, tmp_path: Path):
        prompt = _build_system_prompt(tmp_path)
        assert prompt == ""

    def test_memory_md_not_loaded(self, tmp_path: Path):
        """MEMORY.md should NOT be included in system prompt."""
        (tmp_path / "AGENTS.md").write_text("Agent prompt")
        (tmp_path / "MEMORY.md").write_text("Secret memory data")
        prompt = _build_system_prompt(tmp_path)
        assert "Secret memory data" not in prompt

    def test_load_real_robin_config(self):
        """Load the actual agents/robin/ config."""
        repo_root = Path(__file__).resolve().parent.parent.parent
        robin_dir = repo_root / "agents" / "robin"
        if not robin_dir.exists():
            pytest.skip("agents/robin not found")
        models_path = repo_root / "inotagent" / "models.yml"
        platform_path = repo_root / "inotagent" / "platform.yml"
        if not models_path.exists() or not platform_path.exists():
            pytest.skip("inotagent config files not found")

        models = load_models(models_path)
        platform = load_platform_config(platform_path)
        config = load_agent_config(robin_dir, models, platform)

        assert config.name == "robin"
        assert config.model_id == "nvidia-minimax-2.5"
        assert len(config.fallbacks) > 0
        assert "Robin" in config.system_prompt
