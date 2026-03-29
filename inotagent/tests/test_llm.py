"""Tests for LLM client layer — types, message conversion, response parsing, factory."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from inotagent.config.models import ModelConfig
from inotagent.llm.client import LLMMessage, LLMResponse, ToolCall, TokenUsage, strip_think_tags
from inotagent.llm.anthropic import AnthropicClient, _convert_messages, _parse_response
from inotagent.llm.openai_compat import (
    OpenAICompatClient,
    _convert_messages as oai_convert_messages,
    _convert_tools,
    _parse_response as oai_parse_response,
)
from inotagent.llm.factory import create_client, chat_with_fallback, AllModelsFailed
from inotagent.llm.tokens import count_tokens, count_tokens_message, build_context, estimate_tools_tokens


# --- Shared fixtures ---


@pytest.fixture
def nvidia_model() -> ModelConfig:
    return ModelConfig(
        id="test-nvidia",
        provider="nvidia",
        model="test/model",
        api_key_env="TEST_KEY",
        base_url="https://api.test.com/v1",
        context_window=128000,
        max_tokens=4096,
    )


@pytest.fixture
def anthropic_model() -> ModelConfig:
    return ModelConfig(
        id="test-claude",
        provider="anthropic",
        model="claude-test",
        api_key_env="ANTHROPIC_API_KEY",
        base_url=None,
        context_window=200000,
        max_tokens=8192,
    )


@pytest.fixture
def models(nvidia_model, anthropic_model) -> dict[str, ModelConfig]:
    return {nvidia_model.id: nvidia_model, anthropic_model.id: anthropic_model}


# --- LLM types tests ---


class TestStripThinkTags:
    def test_strips_think_block(self):
        text = "<think>Some reasoning here</think>\n\nHello world"
        assert strip_think_tags(text) == "Hello world"

    def test_strips_multiline_think(self):
        text = "<think>\nLine 1\nLine 2\nLine 3\n</think>\n\nFinal answer"
        assert strip_think_tags(text) == "Final answer"

    def test_no_think_tags(self):
        text = "Hello world"
        assert strip_think_tags(text) == "Hello world"

    def test_empty_string(self):
        assert strip_think_tags("") == ""

    def test_only_think_block(self):
        text = "<think>Just thinking</think>"
        assert strip_think_tags(text) == ""

    def test_multiple_think_blocks(self):
        text = "<think>First</think> Hello <think>Second</think> World"
        assert strip_think_tags(text) == "Hello World"

    def test_preserves_other_tags(self):
        text = "<think>Reasoning</think>\n\n<code>print('hi')</code>"
        assert strip_think_tags(text) == "<code>print('hi')</code>"


class TestLLMTypes:
    def test_token_usage_total(self):
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        assert usage.total_tokens == 150

    def test_token_usage_defaults(self):
        usage = TokenUsage()
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.total_tokens == 0

    def test_llm_message_defaults(self):
        msg = LLMMessage(role="user", content="hello")
        assert msg.tool_calls is None
        assert msg.tool_call_id is None

    def test_llm_response_defaults(self):
        resp = LLMResponse()
        assert resp.content == ""
        assert resp.tool_calls == []
        assert resp.stop_reason == "end_turn"

    def test_tool_call(self):
        tc = ToolCall(id="tc_1", name="shell", arguments={"command": "ls"})
        assert tc.id == "tc_1"
        assert tc.name == "shell"
        assert tc.arguments == {"command": "ls"}


# --- Anthropic message conversion tests ---


class TestAnthropicConvertMessages:
    def test_simple_user_message(self):
        msgs = [LLMMessage(role="user", content="hello")]
        result = _convert_messages(msgs)
        assert result == [{"role": "user", "content": "hello"}]

    def test_assistant_message(self):
        msgs = [LLMMessage(role="assistant", content="hi there")]
        result = _convert_messages(msgs)
        assert result == [{"role": "assistant", "content": "hi there"}]

    def test_tool_result_message(self):
        msgs = [LLMMessage(role="tool", content="file contents", tool_call_id="tc_1")]
        result = _convert_messages(msgs)
        assert result == [{
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": "tc_1",
                "content": "file contents",
            }],
        }]

    def test_assistant_with_tool_calls(self):
        msgs = [LLMMessage(
            role="assistant",
            content="Let me check",
            tool_calls=[ToolCall(id="tc_1", name="shell", arguments={"command": "ls"})],
        )]
        result = _convert_messages(msgs)
        assert len(result) == 1
        content = result[0]["content"]
        assert content[0] == {"type": "text", "text": "Let me check"}
        assert content[1]["type"] == "tool_use"
        assert content[1]["name"] == "shell"

    def test_assistant_with_tool_calls_no_text(self):
        msgs = [LLMMessage(
            role="assistant",
            content="",
            tool_calls=[ToolCall(id="tc_1", name="shell", arguments={"command": "ls"})],
        )]
        result = _convert_messages(msgs)
        # Should NOT include empty text block
        content = result[0]["content"]
        assert len(content) == 1
        assert content[0]["type"] == "tool_use"

    def test_multi_turn_conversation(self):
        msgs = [
            LLMMessage(role="user", content="hello"),
            LLMMessage(role="assistant", content="hi"),
            LLMMessage(role="user", content="how are you"),
        ]
        result = _convert_messages(msgs)
        assert len(result) == 3
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"
        assert result[2]["role"] == "user"


# --- Anthropic response parsing tests ---


class TestAnthropicParseResponse:
    def test_text_response(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="Hello world")]
        mock_response.usage = MagicMock(input_tokens=10, output_tokens=5)
        mock_response.stop_reason = "end_turn"

        result = _parse_response(mock_response)
        assert result.content == "Hello world"
        assert result.tool_calls == []
        assert result.usage.input_tokens == 10
        assert result.usage.output_tokens == 5
        assert result.stop_reason == "end_turn"

    def test_tool_use_response(self):
        text_block = MagicMock(type="text", text="Let me run that")
        tool_block = MagicMock(type="tool_use", id="tc_123", input={"command": "ls -la"})
        # MagicMock treats 'name' specially, must set it after construction
        tool_block.name = "shell"
        mock_response = MagicMock()
        mock_response.content = [text_block, tool_block]
        mock_response.usage = MagicMock(input_tokens=50, output_tokens=30)
        mock_response.stop_reason = "tool_use"

        result = _parse_response(mock_response)
        assert result.content == "Let me run that"
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].id == "tc_123"
        assert result.tool_calls[0].name == "shell"
        assert result.tool_calls[0].arguments == {"command": "ls -la"}
        assert result.stop_reason == "tool_use"

    def test_multiple_tool_calls(self):
        tool1 = MagicMock(type="tool_use", id="tc_1", name="shell", input={"command": "ls"})
        tool2 = MagicMock(type="tool_use", id="tc_2", name="read_file", input={"path": "/tmp/x"})
        mock_response = MagicMock()
        mock_response.content = [tool1, tool2]
        mock_response.usage = MagicMock(input_tokens=20, output_tokens=10)
        mock_response.stop_reason = "tool_use"

        result = _parse_response(mock_response)
        assert len(result.tool_calls) == 2


# --- OpenAI-compat message conversion tests ---


class TestOpenAICompatConvertMessages:
    def test_system_message_prepended(self):
        msgs = [LLMMessage(role="user", content="hello")]
        result = oai_convert_messages("You are helpful", msgs)
        assert result[0] == {"role": "system", "content": "You are helpful"}
        assert result[1] == {"role": "user", "content": "hello"}

    def test_tool_result_format(self):
        msgs = [LLMMessage(role="tool", content="output", tool_call_id="tc_1")]
        result = oai_convert_messages("system", msgs)
        assert result[1] == {
            "role": "tool",
            "tool_call_id": "tc_1",
            "content": "output",
        }

    def test_assistant_with_tool_calls_format(self):
        msgs = [LLMMessage(
            role="assistant",
            content="",
            tool_calls=[ToolCall(id="tc_1", name="shell", arguments={"command": "ls"})],
        )]
        result = oai_convert_messages("system", msgs)
        msg = result[1]
        assert msg["role"] == "assistant"
        assert msg["content"] is None
        assert len(msg["tool_calls"]) == 1
        assert msg["tool_calls"][0]["type"] == "function"
        assert msg["tool_calls"][0]["function"]["name"] == "shell"
        assert json.loads(msg["tool_calls"][0]["function"]["arguments"]) == {"command": "ls"}


# --- OpenAI-compat tool conversion tests ---


class TestOpenAICompatConvertTools:
    def test_anthropic_to_openai_format(self):
        anthropic_tools = [{
            "name": "shell",
            "description": "Run a shell command",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command to run"},
                },
                "required": ["command"],
            },
        }]
        result = _convert_tools(anthropic_tools)
        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "shell"
        assert result[0]["function"]["description"] == "Run a shell command"
        assert result[0]["function"]["parameters"]["type"] == "object"

    def test_empty_tools(self):
        assert _convert_tools([]) == []


# --- OpenAI-compat response parsing tests ---


class TestOpenAICompatParseResponse:
    def test_text_response(self):
        data = {
            "choices": [{
                "message": {"content": "Hello"},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        result = oai_parse_response(data)
        assert result.content == "Hello"
        assert result.tool_calls == []
        assert result.usage.input_tokens == 10
        assert result.usage.output_tokens == 5
        assert result.stop_reason == "end_turn"

    def test_tool_call_response(self):
        data = {
            "choices": [{
                "message": {
                    "content": None,
                    "tool_calls": [{
                        "id": "tc_1",
                        "type": "function",
                        "function": {
                            "name": "shell",
                            "arguments": '{"command": "ls"}',
                        },
                    }],
                },
                "finish_reason": "tool_calls",
            }],
            "usage": {"prompt_tokens": 20, "completion_tokens": 10},
        }
        result = oai_parse_response(data)
        assert result.content == ""
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "shell"
        assert result.tool_calls[0].arguments == {"command": "ls"}
        assert result.stop_reason == "tool_use"

    def test_malformed_arguments(self):
        data = {
            "choices": [{
                "message": {
                    "content": None,
                    "tool_calls": [{
                        "id": "tc_1",
                        "type": "function",
                        "function": {
                            "name": "shell",
                            "arguments": "not valid json{{{",
                        },
                    }],
                },
                "finish_reason": "tool_calls",
            }],
            "usage": {},
        }
        result = oai_parse_response(data)
        assert result.tool_calls[0].arguments == {"raw": "not valid json{{{"}

    def test_missing_usage(self):
        data = {
            "choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}],
        }
        result = oai_parse_response(data)
        assert result.usage.input_tokens == 0
        assert result.usage.output_tokens == 0


# --- Factory tests ---


class TestCreateClient:
    def test_create_nvidia_client(self, nvidia_model):
        client = create_client(nvidia_model)
        assert isinstance(client, OpenAICompatClient)

    def test_create_anthropic_client(self, anthropic_model, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        client = create_client(anthropic_model)
        assert isinstance(client, AnthropicClient)

    def test_openai_compat_without_base_url_raises(self):
        model = ModelConfig(
            id="bad", provider="nvidia", model="x",
            api_key_env="X", base_url=None,
            context_window=1000, max_tokens=100,
        )
        with pytest.raises(ValueError, match="requires base_url"):
            create_client(model)

    def test_unknown_provider_raises(self):
        model = ModelConfig(
            id="bad", provider="unknown_provider", model="x",
            api_key_env="X", base_url="http://x",
            context_window=1000, max_tokens=100,
        )
        with pytest.raises(ValueError, match="Unknown provider"):
            create_client(model)


class TestChatWithFallback:
    async def test_primary_succeeds(self, models):
        expected = LLMResponse(content="hello")

        with patch("inotagent.llm.factory.create_client") as mock_create:
            mock_client = AsyncMock()
            mock_client.chat.return_value = expected
            mock_create.return_value = mock_client

            result = await chat_with_fallback(
                models=models,
                model_id="test-nvidia",
                fallbacks=["test-claude"],
                system="sys",
                messages=[],
                max_tokens=100,
            )

        assert result.content == "hello"
        # Should only call once (primary succeeded)
        assert mock_create.call_count == 1

    async def test_fallback_on_primary_failure(self, models):
        expected = LLMResponse(content="from fallback")

        with patch("inotagent.llm.factory.create_client") as mock_create:
            mock_primary = AsyncMock()
            mock_primary.chat.side_effect = Exception("rate limited")
            mock_fallback = AsyncMock()
            mock_fallback.chat.return_value = expected
            mock_create.side_effect = [mock_primary, mock_fallback]

            result = await chat_with_fallback(
                models=models,
                model_id="test-nvidia",
                fallbacks=["test-claude"],
                system="sys",
                messages=[],
                max_tokens=100,
            )

        assert result.content == "from fallback"
        assert mock_create.call_count == 2

    async def test_all_fail_raises(self, models):
        with patch("inotagent.llm.factory.create_client") as mock_create:
            mock_client = AsyncMock()
            mock_client.chat.side_effect = Exception("fail")
            mock_create.return_value = mock_client

            with pytest.raises(AllModelsFailed):
                await chat_with_fallback(
                    models=models,
                    model_id="test-nvidia",
                    fallbacks=["test-claude"],
                    system="sys",
                    messages=[],
                    max_tokens=100,
                )

    async def test_skips_unknown_fallback(self, models):
        with patch("inotagent.llm.factory.create_client") as mock_create:
            mock_primary = AsyncMock()
            mock_primary.chat.side_effect = Exception("fail")
            mock_fallback = AsyncMock()
            mock_fallback.chat.return_value = LLMResponse(content="ok")
            mock_create.side_effect = [mock_primary, mock_fallback]

            result = await chat_with_fallback(
                models=models,
                model_id="test-nvidia",
                fallbacks=["nonexistent", "test-claude"],
                system="sys",
                messages=[],
                max_tokens=100,
            )

        assert result.content == "ok"


# --- Token counting tests ---


class TestTokenCounting:
    def test_count_tokens_basic(self):
        tokens = count_tokens("Hello, world!")
        assert tokens > 0
        assert tokens < 10

    def test_count_tokens_empty(self):
        assert count_tokens("") == 0

    def test_count_tokens_long_text(self):
        text = "word " * 1000
        tokens = count_tokens(text)
        assert 900 < tokens < 1200  # roughly 1 token per word

    def test_count_tokens_message(self):
        msg = LLMMessage(role="user", content="Hello there")
        tokens = count_tokens_message(msg)
        assert tokens > 0

    def test_count_tokens_message_with_tool_calls(self):
        msg = LLMMessage(
            role="assistant",
            content="running",
            tool_calls=[ToolCall(id="1", name="shell", arguments={"command": "ls -la"})],
        )
        tokens = count_tokens_message(msg)
        assert tokens > count_tokens_message(LLMMessage(role="assistant", content="running"))

    def test_estimate_tools_tokens(self):
        tools = [{
            "name": "shell",
            "description": "Run a shell command",
            "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}},
        }]
        tokens = estimate_tools_tokens(tools)
        assert tokens > 0

    def test_estimate_tools_tokens_none(self):
        assert estimate_tools_tokens(None) == 0
        assert estimate_tools_tokens([]) == 0


class TestBuildContext:
    @pytest.fixture
    def small_model(self) -> ModelConfig:
        return ModelConfig(
            id="small", provider="test", model="test",
            api_key_env=None, base_url=None,
            context_window=100,  # very small for testing
            max_tokens=20,
        )

    def test_keeps_recent_messages(self, small_model):
        history = [
            LLMMessage(role="user", content="a"),
            LLMMessage(role="assistant", content="b"),
            LLMMessage(role="user", content="c"),
        ]
        result = build_context("sys", history, None, small_model)
        # Should keep at least the most recent message
        assert len(result) > 0
        assert result[-1].content == "c"

    def test_drops_oldest_when_over_budget(self):
        model = ModelConfig(
            id="tiny", provider="test", model="test",
            api_key_env=None, base_url=None,
            context_window=200,
            max_tokens=50,
        )
        # Create many messages that exceed budget
        long_content = "word " * 100
        history = [
            LLMMessage(role="user", content=long_content),
            LLMMessage(role="assistant", content=long_content),
            LLMMessage(role="user", content="recent"),
        ]
        result = build_context("system prompt", history, None, model)
        # Should drop old messages, keep recent
        assert len(result) < len(history)
        if result:
            assert result[-1].content == "recent"

    def test_empty_history(self, small_model):
        result = build_context("sys", [], None, small_model)
        assert result == []

    def test_respects_output_reserve(self):
        model = ModelConfig(
            id="m", provider="test", model="test",
            api_key_env=None, base_url=None,
            context_window=500,
            max_tokens=100,
        )
        history = [LLMMessage(role="user", content="hello")]
        # With large reserve, less room for history
        result_small_reserve = build_context("s", history, None, model, reserve_output=50)
        result_large_reserve = build_context("s", history, None, model, reserve_output=400)
        # Large reserve should keep fewer messages (or equal)
        assert len(result_large_reserve) <= len(result_small_reserve)
