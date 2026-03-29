"""Tests for the agent loop."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from inotagent.config.agent import AgentConfig
from inotagent.config.models import ModelConfig
from inotagent.llm.client import LLMMessage, LLMResponse, TokenUsage
from inotagent.loop import AgentLoop


@pytest.fixture
def model_config() -> ModelConfig:
    return ModelConfig(
        id="test-model",
        provider="nvidia",
        model="test/model",
        api_key_env="TEST_KEY",
        base_url="https://api.test.com/v1",
        context_window=128000,
        max_tokens=4096,
    )


@pytest.fixture
def agent_config() -> AgentConfig:
    return AgentConfig(
        name="testbot",
        model_id="test-model",
        fallbacks=["test-fallback"],
        system_prompt="You are a test agent.",
        channels={},
        parallel=False,
    )


@pytest.fixture
def models(model_config: ModelConfig) -> dict[str, ModelConfig]:
    return {model_config.id: model_config}


@pytest.fixture
def agent_loop(agent_config: AgentConfig, models: dict) -> AgentLoop:
    return AgentLoop(config=agent_config, models=models)


class TestAgentLoop:
    async def test_run_returns_response(self, agent_loop):
        expected = LLMResponse(
            content="Hello from LLM",
            usage=TokenUsage(input_tokens=10, output_tokens=5),
        )
        with patch("inotagent.loop.chat_with_fallback", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = expected
            result = await agent_loop.run("hello")

        assert result == "Hello from LLM"

    async def test_run_passes_system_prompt(self, agent_loop):
        with patch("inotagent.loop.chat_with_fallback", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = LLMResponse(content="ok")
            await agent_loop.run("hello")

        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["system"].startswith("You are a test agent.")
        assert "Current Time" in call_kwargs["system"]

    async def test_run_passes_model_id(self, agent_loop):
        with patch("inotagent.loop.chat_with_fallback", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = LLMResponse(content="ok")
            await agent_loop.run("hello")

        call_kwargs = mock_chat.call_args[1]
        assert mock_chat.call_args[1]["model_id"] == "test-model"

    async def test_run_passes_history(self, agent_loop):
        history = [
            LLMMessage(role="user", content="first"),
            LLMMessage(role="assistant", content="response"),
        ]
        with patch("inotagent.loop.chat_with_fallback", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = LLMResponse(content="ok")
            await agent_loop.run("second", history)

        call_kwargs = mock_chat.call_args[1]
        messages = call_kwargs["messages"]
        assert len(messages) == 3  # 2 history + 1 new
        assert messages[0].content == "first"
        assert messages[1].content == "response"
        assert messages[2].content == "second"

    async def test_run_empty_history(self, agent_loop):
        with patch("inotagent.loop.chat_with_fallback", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = LLMResponse(content="ok")
            await agent_loop.run("hello")

        call_kwargs = mock_chat.call_args[1]
        messages = call_kwargs["messages"]
        assert len(messages) == 1
        assert messages[0].role == "user"
        assert messages[0].content == "hello"


class TestAgentLoopConcurrency:
    async def test_is_busy_false_when_idle(self, agent_loop):
        assert agent_loop.is_busy() is False

    async def test_is_busy_true_during_run(self, agent_loop):
        busy_states: list[bool] = []

        async def slow_chat(**kwargs):
            busy_states.append(agent_loop.is_busy())
            await asyncio.sleep(0.1)
            return LLMResponse(content="done")

        with patch("inotagent.loop.chat_with_fallback", side_effect=slow_chat):
            await agent_loop.run("hello")

        assert busy_states == [True]
        assert agent_loop.is_busy() is False

    async def test_sequential_mode_blocks(self, agent_loop):
        """Sequential mode (default) should process one at a time."""
        call_order: list[str] = []

        async def slow_chat(**kwargs):
            msg = kwargs["messages"][-1].content
            call_order.append(f"start-{msg}")
            await asyncio.sleep(0.05)
            call_order.append(f"end-{msg}")
            return LLMResponse(content=f"reply-{msg}")

        with patch("inotagent.loop.chat_with_fallback", side_effect=slow_chat):
            results = await asyncio.gather(
                agent_loop.run("a"),
                agent_loop.run("b"),
            )

        # Sequential: one finishes before the other starts
        assert call_order[0] == "start-a" or call_order[0] == "start-b"
        first = call_order[0].split("-")[1]
        assert call_order[1] == f"end-{first}"

    async def test_parallel_mode_concurrent(self):
        """Parallel mode should allow concurrent processing."""
        config = AgentConfig(
            name="parallel-bot",
            model_id="test-model",
            system_prompt="test",
            parallel=True,
        )
        model = ModelConfig(
            id="test-model", provider="nvidia", model="test",
            api_key_env="X", base_url="http://x",
            context_window=1000, max_tokens=100,
        )
        loop = AgentLoop(config=config, models={"test-model": model})

        active_concurrent: list[int] = []

        async def slow_chat(**kwargs):
            active_concurrent.append(loop._active_count)
            await asyncio.sleep(0.05)
            return LLMResponse(content="ok")

        with patch("inotagent.loop.chat_with_fallback", side_effect=slow_chat):
            await asyncio.gather(
                loop.run("a"),
                loop.run("b"),
            )

        # At some point, both should be active
        assert max(active_concurrent) == 2

    async def test_is_busy_false_after_error(self, agent_loop):
        """is_busy should be False even if run raises."""
        with patch("inotagent.loop.chat_with_fallback", new_callable=AsyncMock) as mock_chat:
            mock_chat.side_effect = Exception("boom")
            with pytest.raises(Exception, match="boom"):
                await agent_loop.run("hello")

        assert agent_loop.is_busy() is False

    async def test_does_not_mutate_history(self, agent_loop):
        """The passed-in history list should not be modified."""
        history = [LLMMessage(role="user", content="old")]
        original_len = len(history)

        with patch("inotagent.loop.chat_with_fallback", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = LLMResponse(content="ok")
            await agent_loop.run("new", history)

        assert len(history) == original_len


class TestMainEntrypoint:
    def test_resolve_paths(self, tmp_path):
        """Test path resolution from agent dir to inotagent config files."""
        from inotagent.main import resolve_paths

        # Create expected structure
        inotagent_dir = tmp_path / "inotagent"
        inotagent_dir.mkdir()
        (inotagent_dir / "models.yml").write_text("models: []\n")
        (inotagent_dir / "platform.yml").write_text("llm:\n  default_model: test\n")
        agent = tmp_path / "agents" / "robin"
        agent.mkdir(parents=True)

        agent_path, models_path, platform_path = resolve_paths(str(agent))
        assert agent_path == agent
        assert models_path == inotagent_dir / "models.yml"
        assert platform_path == inotagent_dir / "platform.yml"

    def test_resolve_paths_missing_agent_dir(self, tmp_path):
        from inotagent.main import resolve_paths

        with pytest.raises(FileNotFoundError, match="Agent directory not found"):
            resolve_paths(str(tmp_path / "nonexistent"))

    def test_resolve_paths_missing_inotagent_dir(self, tmp_path):
        from inotagent.main import resolve_paths

        agent = tmp_path / "agents" / "robin"
        agent.mkdir(parents=True)

        with pytest.raises(FileNotFoundError, match="inotagent directory not found"):
            resolve_paths(str(agent))
