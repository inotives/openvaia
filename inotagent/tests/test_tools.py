"""Tests for the tool system — registry, shell, files, platform, memory, browser, and tool loop."""

from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from inotagent.config.agent import AgentConfig
from inotagent.config.models import ModelConfig
from inotagent.llm.client import LLMMessage, LLMResponse, TokenUsage, ToolCall
from inotagent.loop import AgentLoop
from inotagent.tools.registry import ToolRegistry
from inotagent.tools.setup import create_tool_registry


# --- ToolRegistry tests ---


class TestToolRegistry:
    def test_empty_registry(self):
        reg = ToolRegistry()
        assert reg.get_definitions() == []
        assert reg.has_tools() is False

    def test_register_and_get_definitions(self):
        reg = ToolRegistry()
        handler = AsyncMock(return_value="ok")
        definition = {"name": "test", "description": "A test tool", "input_schema": {}}
        reg.register("test", handler, definition)

        assert reg.has_tools() is True
        defs = reg.get_definitions()
        assert len(defs) == 1
        assert defs[0]["name"] == "test"

    async def test_execute_calls_handler(self):
        reg = ToolRegistry()
        handler = AsyncMock(return_value="result")
        reg.register("my_tool", handler, {"name": "my_tool"})

        result = await reg.execute("my_tool", {"arg1": "val1"})
        assert result == "result"
        handler.assert_awaited_once_with(arg1="val1")

    async def test_execute_unknown_tool(self):
        reg = ToolRegistry()
        result = await reg.execute("nonexistent", {})
        assert "Unknown tool" in result
        assert "nonexistent" in result

    async def test_execute_handler_error(self):
        reg = ToolRegistry()
        handler = AsyncMock(side_effect=ValueError("bad input"))
        reg.register("failing", handler, {"name": "failing"})

        result = await reg.execute("failing", {})
        assert "Error executing tool" in result
        assert "bad input" in result

    def test_multiple_tools(self):
        reg = ToolRegistry()
        for name in ["a", "b", "c"]:
            reg.register(name, AsyncMock(), {"name": name})
        assert len(reg.get_definitions()) == 3


# --- Shell tool tests ---


class TestShellTool:
    async def test_simple_command(self):
        from inotagent.tools.shell import execute

        result = await execute("echo hello")
        assert "hello" in result

    async def test_command_with_stderr(self):
        from inotagent.tools.shell import execute

        result = await execute("echo err >&2")
        assert "err" in result
        assert "STDERR" in result

    async def test_command_failure_exit_code(self):
        from inotagent.tools.shell import execute

        result = await execute("exit 42")
        assert "Exit code: 42" in result

    async def test_command_timeout(self):
        from inotagent.tools.shell import execute

        result = await execute("sleep 10", timeout=1)
        assert "timed out" in result

    async def test_working_directory(self, tmp_path):
        from inotagent.tools.shell import execute

        result = await execute("pwd", working_dir=str(tmp_path))
        assert str(tmp_path) in result

    async def test_no_output(self):
        from inotagent.tools.shell import execute

        result = await execute("true")
        assert result == "(no output)"

    async def test_output_truncation(self):
        from inotagent.tools.shell import execute, MAX_OUTPUT_CHARS

        # Generate output larger than limit
        result = await execute(f"python3 -c \"print('x' * {MAX_OUTPUT_CHARS + 1000})\"")
        assert "truncated" in result

    def test_shell_tool_definition(self):
        from inotagent.tools.shell import SHELL_TOOL

        assert SHELL_TOOL["name"] == "shell"
        assert "command" in SHELL_TOOL["input_schema"]["properties"]
        assert "command" in SHELL_TOOL["input_schema"]["required"]


# --- File tool tests ---


class TestReadFile:
    async def test_read_existing_file(self, tmp_path):
        from inotagent.tools.files import read_file

        f = tmp_path / "test.txt"
        f.write_text("line1\nline2\nline3\n")

        result = await read_file(str(f))
        assert "line1" in result
        assert "line3" in result

    async def test_read_nonexistent_file(self):
        from inotagent.tools.files import read_file

        result = await read_file("/nonexistent/path/file.txt")
        assert "File not found" in result

    async def test_read_max_lines(self, tmp_path):
        from inotagent.tools.files import read_file

        f = tmp_path / "big.txt"
        f.write_text("\n".join(f"line{i}" for i in range(100)))

        result = await read_file(str(f), max_lines=5)
        assert "line4" in result
        assert "truncated" in result

    async def test_read_empty_file(self, tmp_path):
        from inotagent.tools.files import read_file

        f = tmp_path / "empty.txt"
        f.write_text("")

        result = await read_file(str(f))
        assert result == "(empty file)"

    async def test_read_directory_error(self, tmp_path):
        from inotagent.tools.files import read_file

        result = await read_file(str(tmp_path))
        assert "directory" in result.lower()


class TestListFiles:
    async def test_list_directory(self, tmp_path):
        from inotagent.tools.files import list_files

        (tmp_path / "a.py").write_text("")
        (tmp_path / "b.txt").write_text("")
        (tmp_path / "subdir").mkdir()

        result = await list_files(str(tmp_path))
        assert "a.py" in result
        assert "b.txt" in result
        assert "subdir/" in result

    async def test_list_with_pattern(self, tmp_path):
        from inotagent.tools.files import list_files

        (tmp_path / "a.py").write_text("")
        (tmp_path / "b.txt").write_text("")

        result = await list_files(str(tmp_path), pattern="*.py")
        assert "a.py" in result
        assert "b.txt" not in result

    async def test_list_nonexistent_dir(self):
        from inotagent.tools.files import list_files

        result = await list_files("/nonexistent/dir")
        assert "not found" in result.lower()

    async def test_list_no_matches(self, tmp_path):
        from inotagent.tools.files import list_files

        (tmp_path / "a.py").write_text("")

        result = await list_files(str(tmp_path), pattern="*.rs")
        assert "No files matching" in result


class TestSearchFiles:
    async def test_search_finds_match(self, tmp_path):
        from inotagent.tools.files import search_files

        (tmp_path / "code.py").write_text("def hello():\n    return 'world'\n")

        result = await search_files("hello", str(tmp_path))
        assert "code.py" in result
        assert "hello" in result

    async def test_search_no_match(self, tmp_path):
        from inotagent.tools.files import search_files

        (tmp_path / "code.py").write_text("def foo(): pass\n")

        result = await search_files("nonexistent_pattern", str(tmp_path))
        assert "No matches" in result

    async def test_search_with_glob_filter(self, tmp_path):
        from inotagent.tools.files import search_files

        (tmp_path / "code.py").write_text("hello\n")
        (tmp_path / "notes.txt").write_text("hello\n")

        result = await search_files("hello", str(tmp_path), glob="*.py")
        assert "code.py" in result
        assert "notes.txt" not in result

    async def test_search_invalid_regex(self, tmp_path):
        from inotagent.tools.files import search_files

        result = await search_files("[invalid", str(tmp_path))
        assert "Invalid regex" in result

    async def test_search_nonexistent_dir(self):
        from inotagent.tools.files import search_files

        result = await search_files("pattern", "/nonexistent/dir")
        assert "not found" in result.lower()

    def test_file_tool_definitions(self):
        from inotagent.tools.files import FILE_TOOLS

        assert len(FILE_TOOLS) == 3
        names = [t["name"] for t in FILE_TOOLS]
        assert "read_file" in names
        assert "list_files" in names
        assert "search_files" in names


# --- Browser tool tests ---


class TestBrowserTool:
    async def test_ensure_browser_error_propagates(self):
        from inotagent.tools.browser import BrowserTool

        bt = BrowserTool()

        # Patch _ensure_browser to simulate playwright not being available
        async def fake_ensure():
            raise RuntimeError("Playwright is not installed")

        bt._ensure_browser = fake_ensure
        result = await bt.execute(url="http://example.com")
        assert "error" in result.lower()

    def test_browser_tool_definition(self):
        from inotagent.tools.browser import BROWSER_TOOL

        assert BROWSER_TOOL["name"] == "browser"
        assert "url" in BROWSER_TOOL["input_schema"]["required"]
        assert "action" in BROWSER_TOOL["input_schema"]["properties"]

    async def test_close_no_browser(self):
        from inotagent.tools.browser import BrowserTool

        bt = BrowserTool()
        await bt.close()  # should not raise


# --- Platform tool tests ---


class TestPlatformTools:
    async def test_task_list_no_db(self):
        from inotagent.tools.platform import PlatformTools

        pt = PlatformTools(agent_name="test")
        result = await pt.task_list()
        assert "not connected" in result.lower() or "not configured" in result.lower()

    async def test_task_create_no_db(self):
        from inotagent.tools.platform import PlatformTools

        pt = PlatformTools(agent_name="test")
        result = await pt.task_create(title="Test", assigned_to="robin")
        assert "not connected" in result.lower() or "not configured" in result.lower()

    async def test_task_update_no_db(self):
        from inotagent.tools.platform import PlatformTools

        pt = PlatformTools(agent_name="test")
        result = await pt.task_update(key="INO-001", status="done")
        assert "not connected" in result.lower() or "not configured" in result.lower()

    async def test_send_message_no_db(self):
        from inotagent.tools.platform import PlatformTools

        pt = PlatformTools(agent_name="test")
        result = await pt.send_message(space_name="public", body="hello")
        assert "not connected" in result.lower() or "not configured" in result.lower()

    def test_platform_tool_definitions(self):
        from inotagent.tools.platform import PLATFORM_TOOLS

        assert len(PLATFORM_TOOLS) == 5
        names = [t["name"] for t in PLATFORM_TOOLS]
        assert "task_list" in names
        assert "task_update" in names
        assert "task_create" in names
        assert "send_message" in names
        assert "skill_create" in names


# --- Memory tool tests ---


class TestMemoryTools:
    async def test_memory_store_no_db(self):
        from inotagent.tools.memory import MemoryTools

        mt = MemoryTools(agent_name="test")
        result = await mt.memory_store(content="remember this", tags=["test"], tier="short")
        assert "not connected" in result.lower() or "not configured" in result.lower()

    async def test_memory_search_no_db(self):
        from inotagent.tools.memory import MemoryTools

        mt = MemoryTools(agent_name="test")
        result = await mt.memory_search(query="something")
        assert "not connected" in result.lower() or "not configured" in result.lower()

    def test_memory_tool_definitions(self):
        from inotagent.tools.memory import MEMORY_TOOLS

        assert len(MEMORY_TOOLS) == 2
        names = [t["name"] for t in MEMORY_TOOLS]
        assert "memory_store" in names
        assert "memory_search" in names


# --- Tool setup tests ---


class TestCreateToolRegistry:
    def test_creates_all_tools(self):
        reg = create_tool_registry(agent_name="test")
        defs = reg.get_definitions()
        names = [d["name"] for d in defs]

        assert "shell" in names
        assert "read_file" in names
        assert "list_files" in names
        assert "search_files" in names
        assert "browser" in names
        assert "task_list" in names
        assert "task_update" in names
        assert "task_create" in names
        assert "send_message" in names
        assert "memory_store" in names
        assert "memory_search" in names

    def test_total_tool_count(self):
        reg = create_tool_registry(agent_name="test")
        assert len(reg.get_definitions()) >= 19

    async def test_shell_tool_works(self):
        reg = create_tool_registry(agent_name="test")
        result = await reg.execute("shell", {"command": "echo hello"})
        assert "hello" in result

    async def test_file_tools_work(self, tmp_path):
        reg = create_tool_registry(agent_name="test")
        f = tmp_path / "test.txt"
        f.write_text("content")

        result = await reg.execute("read_file", {"path": str(f)})
        assert "content" in result


# --- Tool call loop integration tests ---


class TestToolCallLoop:
    @pytest.fixture
    def model_config(self):
        return ModelConfig(
            id="test-model", provider="nvidia", model="test/model",
            api_key_env="TEST_KEY", base_url="https://api.test.com/v1",
            context_window=128000, max_tokens=4096,
        )

    @pytest.fixture
    def agent_config(self):
        return AgentConfig(
            name="testbot", model_id="test-model",
            system_prompt="You are a test agent.",
        )

    @pytest.fixture
    def models(self, model_config):
        return {model_config.id: model_config}

    async def test_no_tool_calls(self, agent_config, models):
        """When LLM returns no tool calls, return content directly."""
        reg = ToolRegistry()
        reg.register("shell", AsyncMock(), {"name": "shell"})
        loop = AgentLoop(config=agent_config, models=models, tool_registry=reg)

        with patch("inotagent.loop.chat_with_fallback", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = LLMResponse(content="Just a reply")
            result = await loop.run("hello")

        assert result == "Just a reply"
        mock_chat.assert_awaited_once()

    async def test_single_tool_call(self, agent_config, models):
        """LLM calls one tool, gets result, returns final response."""
        reg = ToolRegistry()
        reg.register("shell", AsyncMock(return_value="hello world"), {"name": "shell"})
        loop = AgentLoop(config=agent_config, models=models, tool_registry=reg)

        call_count = 0

        async def mock_chat(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return LLMResponse(
                    content="",
                    tool_calls=[ToolCall(id="tc1", name="shell", arguments={"command": "echo hello"})],
                )
            else:
                return LLMResponse(content="The output was: hello world")

        with patch("inotagent.loop.chat_with_fallback", side_effect=mock_chat):
            result = await loop.run("run echo hello")

        assert result == "The output was: hello world"
        assert call_count == 2

    async def test_multiple_tool_calls_in_one_response(self, agent_config, models):
        """LLM returns multiple tool calls in a single response."""
        handler_a = AsyncMock(return_value="result_a")
        handler_b = AsyncMock(return_value="result_b")
        reg = ToolRegistry()
        reg.register("tool_a", handler_a, {"name": "tool_a"})
        reg.register("tool_b", handler_b, {"name": "tool_b"})
        loop = AgentLoop(config=agent_config, models=models, tool_registry=reg)

        call_count = 0

        async def mock_chat(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return LLMResponse(
                    content="",
                    tool_calls=[
                        ToolCall(id="tc1", name="tool_a", arguments={"x": 1}),
                        ToolCall(id="tc2", name="tool_b", arguments={"y": 2}),
                    ],
                )
            else:
                return LLMResponse(content="Both done")

        with patch("inotagent.loop.chat_with_fallback", side_effect=mock_chat):
            result = await loop.run("do both")

        assert result == "Both done"
        handler_a.assert_awaited_once_with(x=1)
        handler_b.assert_awaited_once_with(y=2)

    async def test_chained_tool_calls(self, agent_config, models):
        """LLM does tool call → result → another tool call → result → final."""
        reg = ToolRegistry()
        reg.register("shell", AsyncMock(return_value="output"), {"name": "shell"})
        loop = AgentLoop(config=agent_config, models=models, tool_registry=reg)

        call_count = 0

        async def mock_chat(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return LLMResponse(
                    content="",
                    tool_calls=[ToolCall(id="tc1", name="shell", arguments={"command": "ls"})],
                )
            elif call_count == 2:
                return LLMResponse(
                    content="",
                    tool_calls=[ToolCall(id="tc2", name="shell", arguments={"command": "cat file"})],
                )
            else:
                return LLMResponse(content="All done")

        with patch("inotagent.loop.chat_with_fallback", side_effect=mock_chat):
            result = await loop.run("read files")

        assert result == "All done"
        assert call_count == 3

    async def test_max_iterations_limit(self, agent_config, models):
        """Tool loop should stop after MAX_TOOL_ITERATIONS."""
        from inotagent.loop import MAX_TOOL_ITERATIONS

        reg = ToolRegistry()
        reg.register("shell", AsyncMock(return_value="ok"), {"name": "shell"})
        loop = AgentLoop(config=agent_config, models=models, tool_registry=reg)

        call_count = 0

        async def infinite_tools(**kwargs):
            nonlocal call_count
            call_count += 1
            return LLMResponse(
                content=f"iteration {call_count}",
                tool_calls=[ToolCall(id=f"tc{call_count}", name="shell", arguments={"command": "echo"})],
            )

        with patch("inotagent.loop.chat_with_fallback", side_effect=infinite_tools):
            result = await loop.run("infinite loop")

        # Should have stopped at MAX_TOOL_ITERATIONS + 1 (initial + iterations)
        assert call_count == MAX_TOOL_ITERATIONS + 1

    async def test_tool_error_returned_to_llm(self, agent_config, models):
        """When a tool fails, error message is sent back to LLM."""
        reg = ToolRegistry()
        # Don't register "nonexistent" — will trigger unknown tool error
        reg.register("shell", AsyncMock(), {"name": "shell"})
        loop = AgentLoop(config=agent_config, models=models, tool_registry=reg)

        call_count = 0

        async def mock_chat(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return LLMResponse(
                    content="",
                    tool_calls=[ToolCall(id="tc1", name="nonexistent", arguments={})],
                )
            else:
                # Check that the tool result message contains the error
                messages = kwargs["messages"]
                tool_msg = [m for m in messages if m.role == "tool"]
                assert len(tool_msg) == 1
                assert "Unknown tool" in tool_msg[0].content
                return LLMResponse(content="Sorry, that tool doesn't exist")

        with patch("inotagent.loop.chat_with_fallback", side_effect=mock_chat):
            result = await loop.run("use bad tool")

        assert result == "Sorry, that tool doesn't exist"

    async def test_no_registry_no_tools(self, agent_config, models):
        """Without a tool registry, no tools are sent to the LLM."""
        loop = AgentLoop(config=agent_config, models=models)

        with patch("inotagent.loop.chat_with_fallback", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = LLMResponse(content="No tools")
            await loop.run("hello")

        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs.get("tools") is None

    async def test_tool_results_in_messages(self, agent_config, models):
        """Verify tool call results are properly added to message history."""
        reg = ToolRegistry()
        reg.register("shell", AsyncMock(return_value="42"), {"name": "shell"})
        loop = AgentLoop(config=agent_config, models=models, tool_registry=reg)

        call_count = 0

        async def mock_chat(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return LLMResponse(
                    content="Let me check",
                    tool_calls=[ToolCall(id="tc1", name="shell", arguments={"command": "echo 42"})],
                )
            else:
                messages = kwargs["messages"]
                # Should have: user, assistant (with tool calls), tool result
                assert messages[-2].role == "assistant"
                assert messages[-2].tool_calls is not None
                assert messages[-1].role == "tool"
                assert messages[-1].content == "42"
                assert messages[-1].tool_call_id == "tc1"
                return LLMResponse(content="The answer is 42")

        with patch("inotagent.loop.chat_with_fallback", side_effect=mock_chat):
            result = await loop.run("what is the answer?")

        assert result == "The answer is 42"


# --- Main setup_channels test update (tool registry integration) ---


class TestMainToolIntegration:
    def test_setup_creates_tool_registry(self):
        """Verify main.py wires up tool registry into agent loop."""
        reg = create_tool_registry(agent_name="ino", default_working_dir="/home/agent")
        assert reg.has_tools()
        assert len(reg.get_definitions()) >= 19


# --- Embedding client tests ---


class TestEmbeddingClient:
    def test_init_no_config(self):
        """No model configured → returns False."""
        from inotagent.config.platform import EmbeddingConfig
        from inotagent.llm.embeddings import init_embedding_client
        config = EmbeddingConfig(model="", dimensions=1024, base_url="", api_key_env="")
        assert init_embedding_client(config) is False

    def test_init_no_api_key(self, monkeypatch):
        """API key env set but empty → returns False."""
        from inotagent.config.platform import EmbeddingConfig
        from inotagent.llm.embeddings import init_embedding_client
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        config = EmbeddingConfig(
            model="nvidia/test-embed",
            dimensions=1024,
            base_url="https://api.test.com/v1",
            api_key_env="NVIDIA_API_KEY",
        )
        assert init_embedding_client(config) is False

    def test_init_success(self, monkeypatch):
        """Valid config + API key → returns True."""
        from inotagent.config.platform import EmbeddingConfig
        from inotagent.llm.embeddings import init_embedding_client
        monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
        config = EmbeddingConfig(
            model="nvidia/test-embed",
            dimensions=1024,
            base_url="https://api.test.com/v1",
            api_key_env="NVIDIA_API_KEY",
        )
        assert init_embedding_client(config) is True

    async def test_embed_one(self):
        """EmbeddingClient.embed_one returns a vector."""
        from inotagent.config.platform import EmbeddingConfig
        from inotagent.llm.embeddings import EmbeddingClient

        config = EmbeddingConfig(
            model="test/model", dimensions=3,
            base_url="https://api.test.com/v1", api_key_env="",
        )
        client = EmbeddingClient(config)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"index": 0, "embedding": [0.1, 0.2, 0.3]}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_ctx = AsyncMock()
            mock_ctx.post.return_value = mock_response
            mock_httpx.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_httpx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await client.embed_one("hello world", input_type="query")

        assert result == [0.1, 0.2, 0.3]
        call_kwargs = mock_ctx.post.call_args
        assert call_kwargs[1]["json"]["input_type"] == "query"
        assert call_kwargs[1]["json"]["model"] == "test/model"

    async def test_embed_batch_sorted_by_index(self):
        """Batch embeddings are sorted by index."""
        from inotagent.config.platform import EmbeddingConfig
        from inotagent.llm.embeddings import EmbeddingClient

        config = EmbeddingConfig(
            model="test/model", dimensions=2,
            base_url="https://api.test.com/v1", api_key_env="",
        )
        client = EmbeddingClient(config)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"index": 1, "embedding": [0.3, 0.4]},
                {"index": 0, "embedding": [0.1, 0.2]},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_ctx = AsyncMock()
            mock_ctx.post.return_value = mock_response
            mock_httpx.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_httpx.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await client.embed(["a", "b"])

        assert result == [[0.1, 0.2], [0.3, 0.4]]


# --- Prompt gen tests ---


class TestPromptGen:
    def test_system_prompt_exists(self):
        from inotagent.llm.prompt_gen import PROMPT_GEN_SYSTEM
        assert len(PROMPT_GEN_SYSTEM) > 100
        assert "OpenVAIA" in PROMPT_GEN_SYSTEM
        assert "single pass" in PROMPT_GEN_SYSTEM

    async def test_enhance_prompt_success(self):
        from inotagent.config.models import ModelConfig
        from inotagent.config.platform import PromptGenConfig
        from inotagent.llm.prompt_gen import enhance_prompt

        config = PromptGenConfig(
            default_model="test-model",
            fallbacks=[],
            max_tokens=512,
        )
        model = ModelConfig(
            id="test-model", provider="nvidia", model="test/m",
            api_key_env="X", base_url="http://x",
            context_window=4096, max_tokens=512,
        )
        models = {"test-model": model}

        mock_client = AsyncMock()
        from inotagent.llm.client import LLMResponse
        mock_client.chat.return_value = LLMResponse(content="Enhanced: do the thing properly")

        with patch("inotagent.llm.prompt_gen.create_client", return_value=mock_client):
            result, model_used = await enhance_prompt("do the thing", config, models)

        assert "Enhanced" in result
        assert model_used == "test-model"

    async def test_enhance_prompt_fallback(self):
        from inotagent.config.models import ModelConfig
        from inotagent.config.platform import PromptGenConfig
        from inotagent.llm.prompt_gen import enhance_prompt

        config = PromptGenConfig(
            default_model="bad-model",
            fallbacks=["good-model"],
            max_tokens=512,
        )
        bad = ModelConfig(id="bad-model", provider="nvidia", model="bad/m", api_key_env="X", base_url="http://x", context_window=4096, max_tokens=512)
        good = ModelConfig(id="good-model", provider="nvidia", model="good/m", api_key_env="X", base_url="http://x", context_window=4096, max_tokens=512)
        models = {"bad-model": bad, "good-model": good}

        call_count = 0
        def mock_create(cfg):
            nonlocal call_count
            call_count += 1
            client = AsyncMock()
            from inotagent.llm.client import LLMResponse
            if call_count == 1:
                client.chat.side_effect = Exception("rate limited")
            else:
                client.chat.return_value = LLMResponse(content="Fallback result")
            return client

        with patch("inotagent.llm.prompt_gen.create_client", side_effect=mock_create):
            result, model_used = await enhance_prompt("test", config, models)

        assert result == "Fallback result"
        assert model_used == "good-model"

    async def test_skill_create_no_db(self):
        from inotagent.tools.platform import PlatformTools
        pt = PlatformTools(agent_name="test", db_available=False)
        result = await pt.skill_create(name="test", description="d", content="c", tags=["t"])
        assert "not connected" in result.lower()

    async def test_skill_create_with_db(self):
        from inotagent.tools.platform import PlatformTools
        pt = PlatformTools(agent_name="robin", db_available=True)

        mock_conn = AsyncMock()
        # First query: check if exists → return None
        mock_cur_check = AsyncMock()
        mock_cur_check.fetchone.return_value = None
        # Second query: insert
        mock_cur_insert = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=[mock_cur_check, mock_cur_insert])
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)

        with patch("inotagent.db.pool.get_connection", return_value=mock_conn):
            with patch("inotagent.db.pool.get_schema", return_value="platform"):
                result = await pt.skill_create(
                    name="test_skill", description="A test", content="## Test", tags=["test"],
                )

        assert "draft" in result.lower()
        # Verify insert was called with status='draft' and created_by='robin'
        insert_call = mock_conn.execute.call_args_list[1]
        assert "draft" in insert_call[0][0]
        assert insert_call[0][1][-1] == "robin"  # created_by

class TestDelegateTool:
    async def test_delegate_no_db(self):
        from inotagent.tools.delegate import DelegateTool
        dt = DelegateTool(agent_name="test", models={}, config=MagicMock(), db_available=False)
        result = await dt.delegate(skill="code_review", task="review this")
        assert "not connected" in result.lower()

    async def test_delegate_skill_not_found(self):
        from inotagent.tools.delegate import DelegateTool
        dt = DelegateTool(agent_name="test", models={}, config=MagicMock(), db_available=True)

        with patch("inotagent.db.skills.load_skill_by_name", new_callable=AsyncMock, return_value=None):
            result = await dt.delegate(skill="nonexistent", task="test")
        assert "not found" in result.lower()

    async def test_delegate_success(self):
        from inotagent.config.models import ModelConfig
        from inotagent.tools.delegate import DelegateTool
        from inotagent.llm.client import LLMResponse

        model = ModelConfig(id="test-model", provider="nvidia", model="test/m", api_key_env="X", base_url="http://x", context_window=4096, max_tokens=512)
        config = MagicMock()
        config.model_id = "test-model"
        config.fallbacks = []

        dt = DelegateTool(agent_name="robin", models={"test-model": model}, config=config, db_available=True)
        skill_data = {"id": 1, "name": "code_review", "content": "Review code carefully", "tags": ["review"]}

        with patch("inotagent.db.skills.load_skill_by_name", new_callable=AsyncMock, return_value=skill_data):
            with patch("inotagent.llm.factory.chat_with_fallback", new_callable=AsyncMock, return_value=LLMResponse(content="Code looks good.")):
                result = await dt.delegate(skill="code_review", task="review this diff")

        assert "Code looks good" in result

    async def test_delegate_model_override(self):
        from inotagent.config.models import ModelConfig
        from inotagent.tools.delegate import DelegateTool
        from inotagent.llm.client import LLMResponse

        model_a = ModelConfig(id="model-a", provider="nvidia", model="a", api_key_env="X", base_url="http://x", context_window=4096, max_tokens=512)
        model_b = ModelConfig(id="model-b", provider="nvidia", model="b", api_key_env="X", base_url="http://x", context_window=4096, max_tokens=512)
        config = MagicMock()
        config.model_id = "model-a"
        config.fallbacks = []

        dt = DelegateTool(agent_name="robin", models={"model-a": model_a, "model-b": model_b}, config=config, db_available=True)
        skill_data = {"id": 1, "name": "test", "content": "Test skill", "tags": []}

        with patch("inotagent.db.skills.load_skill_by_name", new_callable=AsyncMock, return_value=skill_data):
            with patch("inotagent.llm.factory.chat_with_fallback", new_callable=AsyncMock, return_value=LLMResponse(content="ok")) as mock_chat:
                await dt.delegate(skill="test", task="test", model="model-b")

        assert mock_chat.call_args[1]["model_id"] == "model-b"


class TestAgentEnv:
    def test_load_agent_env(self, tmp_path):
        from inotagent.config.env import load_agent_env
        env_file = tmp_path / ".env"
        env_file.write_text("KEY1=value1\nKEY2=value2\n# comment\nEMPTY=\n")
        result = load_agent_env(env_file)
        assert result["KEY1"] == "value1"
        assert result["KEY2"] == "value2"
        assert result["EMPTY"] == ""

    def test_load_agent_env_missing(self, tmp_path):
        from inotagent.config.env import load_agent_env
        result = load_agent_env(tmp_path / "nonexistent.env")
        assert result == {}

    def test_load_agent_env_quoted(self, tmp_path):
        from inotagent.config.env import load_agent_env
        env_file = tmp_path / ".env"
        env_file.write_text('KEY1="quoted value"\nKEY2=\'single quoted\'\n')
        result = load_agent_env(env_file)
        assert result["KEY1"] == "quoted value"
        assert result["KEY2"] == "single quoted"


class TestRecurringTasks:
    def test_parse_recurrence_daily(self):
        from inotagent.tools.platform import parse_recurrence
        assert parse_recurrence(["research", "schedule:daily"]) == (1440, None)

    def test_parse_recurrence_hourly(self):
        from inotagent.tools.platform import parse_recurrence
        assert parse_recurrence(["schedule:hourly", "crypto"]) == (60, None)

    def test_parse_recurrence_weekly(self):
        from inotagent.tools.platform import parse_recurrence
        assert parse_recurrence(["schedule:weekly"]) == (10080, None)

    def test_parse_recurrence_5m(self):
        from inotagent.tools.platform import parse_recurrence
        assert parse_recurrence(["schedule:5m"]) == (5, None)

    def test_parse_recurrence_daily_at_time(self):
        from inotagent.tools.platform import parse_recurrence
        assert parse_recurrence(["schedule:daily@09:00"]) == (1440, "09:00")

    def test_parse_recurrence_daily_at_midnight(self):
        from inotagent.tools.platform import parse_recurrence
        assert parse_recurrence(["schedule:daily@00:00"]) == (1440, "00:00")

    def test_parse_recurrence_none(self):
        from inotagent.tools.platform import parse_recurrence
        assert parse_recurrence(["research", "crypto"]) == (None, None)

    def test_parse_recurrence_empty(self):
        from inotagent.tools.platform import parse_recurrence
        assert parse_recurrence([]) == (None, None)

    def test_parse_recurrence_unknown_schedule(self):
        from inotagent.tools.platform import parse_recurrence
        assert parse_recurrence(["schedule:unknown"]) == (None, None)


class TestResourceTools:
    async def test_resource_search_no_db(self):
        from inotagent.tools.resources import ResourceTools
        rt = ResourceTools(agent_name="test", db_available=False)
        result = await rt.resource_search(tags=["crypto"])
        assert "not connected" in result.lower()

    async def test_resource_add_no_db(self):
        from inotagent.tools.resources import ResourceTools
        rt = ResourceTools(agent_name="test", db_available=False)
        result = await rt.resource_add(url="http://x", name="x", description="x", tags=["x"])
        assert "not connected" in result.lower()

    async def test_resource_add_with_db(self):
        from inotagent.tools.resources import ResourceTools
        rt = ResourceTools(agent_name="ino", db_available=True)

        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)

        with patch("inotagent.db.resources.get_connection", return_value=mock_conn):
            with patch("inotagent.db.resources.get_schema", return_value="platform"):
                result = await rt.resource_add(
                    url="https://api.test.com", name="Test API",
                    description="Test data", tags=["test"], notes="Free tier",
                )

        assert "draft" in result.lower()
        # Verify insert was called with 'draft' status and created_by='ino'
        insert_call = mock_conn.execute.call_args
        assert "draft" in insert_call[0][0]
        assert insert_call[0][1][-1] == "ino"

    def test_resource_tool_definitions(self):
        from inotagent.tools.resources import RESOURCE_TOOLS
        assert len(RESOURCE_TOOLS) == 2
        names = [t["name"] for t in RESOURCE_TOOLS]
        assert "resource_search" in names
        assert "resource_add" in names


class TestEmailTool:
    def test_markdown_to_html_headers(self):
        from inotagent.tools.email import markdown_to_html
        html = markdown_to_html("# Title\n\n## Subtitle\n\n### Section")
        assert "<h1>Title</h1>" in html
        assert "<h2>Subtitle</h2>" in html
        assert "<h3>Section</h3>" in html

    def test_markdown_to_html_bold_italic(self):
        from inotagent.tools.email import markdown_to_html
        html = markdown_to_html("**bold** and *italic*")
        assert "<strong>bold</strong>" in html
        assert "<em>italic</em>" in html

    def test_markdown_to_html_code_block(self):
        from inotagent.tools.email import markdown_to_html
        html = markdown_to_html("```python\nprint('hi')\n```")
        assert "<pre" in html
        assert "print('hi')" in html

    def test_markdown_to_html_link(self):
        from inotagent.tools.email import markdown_to_html
        html = markdown_to_html("[Google](https://google.com)")
        assert 'href="https://google.com"' in html
        assert "Google" in html

    async def test_send_email_no_password(self, monkeypatch):
        from inotagent.tools.email import EmailTool
        monkeypatch.setenv("GIT_EMAIL", "test@test.com")
        monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
        tool = EmailTool(agent_name="test")
        result = await tool.send_email(subject="Test", body="Body", to="x@x.com")
        assert "GMAIL_APP_PASSWORD" in result

    async def test_send_email_no_owner(self, monkeypatch):
        from inotagent.tools.email import EmailTool
        monkeypatch.setenv("GIT_EMAIL", "test@test.com")
        monkeypatch.setenv("GMAIL_APP_PASSWORD", "abc")
        monkeypatch.delenv("OWNER_EMAIL", raising=False)
        tool = EmailTool(agent_name="test")
        result = await tool.send_email(subject="Test", body="Body", to="x@x.com")
        assert "OWNER_EMAIL" in result

    async def test_send_email_blocked_recipient(self, monkeypatch):
        from inotagent.tools.email import EmailTool
        monkeypatch.setenv("GIT_EMAIL", "test@test.com")
        monkeypatch.setenv("GMAIL_APP_PASSWORD", "abc")
        monkeypatch.setenv("OWNER_EMAIL", "owner@test.com")
        tool = EmailTool(agent_name="test")
        result = await tool.send_email(subject="Test", body="Body", to="hacker@evil.com")
        assert "not in the allowed" in result

    async def test_send_email_success(self, monkeypatch):
        from inotagent.tools.email import EmailTool
        monkeypatch.setenv("GIT_EMAIL", "agent@test.com")
        monkeypatch.setenv("GMAIL_APP_PASSWORD", "abc123")
        monkeypatch.setenv("OWNER_EMAIL", "owner@test.com")
        tool = EmailTool(agent_name="test")

        with patch("inotagent.tools.email.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            result = await tool.send_email(subject="Report", body="# Hello\n\nWorld", to="owner@test.com")

        assert "Email sent" in result
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("agent@test.com", "abc123")
        mock_server.send_message.assert_called_once()


class TestPromptGen:
    async def test_enhance_prompt_all_fail(self):
        from inotagent.config.models import ModelConfig
        from inotagent.config.platform import PromptGenConfig
        from inotagent.llm.prompt_gen import enhance_prompt

        config = PromptGenConfig(default_model="bad-model", fallbacks=[], max_tokens=512)
        bad = ModelConfig(id="bad-model", provider="nvidia", model="bad/m", api_key_env="X", base_url="http://x", context_window=4096, max_tokens=512)
        models = {"bad-model": bad}

        mock_client = AsyncMock()
        mock_client.chat.side_effect = Exception("API down")

        with patch("inotagent.llm.prompt_gen.create_client", return_value=mock_client):
            with pytest.raises(RuntimeError, match="All prompt gen models failed"):
                await enhance_prompt("test", config, models)
