"""Tests for Phase 4 — persistence layer, context management, and tool result truncation."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from inotagent.config.agent import AgentConfig
from inotagent.config.models import ModelConfig
from inotagent.llm.client import LLMMessage, LLMResponse, TokenUsage, ToolCall
from inotagent.llm.tokens import build_context, count_tokens, estimate_tools_tokens
from inotagent.loop import AgentLoop
from inotagent.tools.registry import ToolRegistry


# --- Tool result truncation tests ---


class TestTruncateToolResult:
    def test_short_result_unchanged(self):
        from inotagent.db.conversations import truncate_tool_result

        result = "short output"
        assert truncate_tool_result(result) == result

    def test_exact_limit_unchanged(self):
        from inotagent.db.conversations import truncate_tool_result, MAX_TOOL_RESULT_CHARS

        result = "x" * MAX_TOOL_RESULT_CHARS
        assert truncate_tool_result(result) == result

    def test_long_result_truncated(self):
        from inotagent.db.conversations import truncate_tool_result, MAX_TOOL_RESULT_CHARS

        result = "x" * (MAX_TOOL_RESULT_CHARS * 3)
        truncated = truncate_tool_result(result)
        assert len(truncated) < len(result)
        assert "truncated" in truncated

    def test_truncated_keeps_start_and_end(self):
        from inotagent.db.conversations import truncate_tool_result, MAX_TOOL_RESULT_CHARS

        start = "START_" + "a" * 1000
        end = "b" * 1000 + "_END"
        middle = "m" * (MAX_TOOL_RESULT_CHARS * 2)
        result = start + middle + end
        truncated = truncate_tool_result(result)
        assert truncated.startswith("START_")
        assert truncated.endswith("_END")


# --- Context window management tests ---


class TestBuildContext:
    @pytest.fixture
    def model_config(self):
        return ModelConfig(
            id="test-model", provider="nvidia", model="test/model",
            api_key_env="X", base_url="http://x",
            context_window=4096, max_tokens=1024,
        )

    def test_fits_all_messages(self, model_config):
        messages = [
            LLMMessage(role="user", content="hello"),
            LLMMessage(role="assistant", content="hi"),
            LLMMessage(role="user", content="how are you?"),
        ]
        result = build_context("system", messages, None, model_config)
        assert len(result) == 3

    def test_drops_oldest_when_over_budget(self, model_config):
        # Create a model with tiny context
        tiny = ModelConfig(
            id="tiny", provider="nvidia", model="t",
            api_key_env="X", base_url="http://x",
            context_window=200, max_tokens=50,
        )
        messages = [
            LLMMessage(role="user", content="word " * 200),
            LLMMessage(role="assistant", content="word " * 200),
            LLMMessage(role="user", content="short"),
        ]
        result = build_context("sys", messages, None, tiny)
        # Should keep newest messages, drop oldest
        assert len(result) < len(messages)
        assert result[-1].content == "short"

    def test_empty_history(self, model_config):
        result = build_context("system", [], None, model_config)
        assert result == []

    def test_tools_reduce_available_budget(self, model_config):
        tools = [{"name": f"tool_{i}", "description": "x" * 100, "input_schema": {}} for i in range(20)]
        messages = [LLMMessage(role="user", content="x " * 200) for _ in range(10)]
        with_tools = build_context("sys", messages, tools, model_config)
        without_tools = build_context("sys", messages, None, model_config)
        # Tools take up budget, so fewer messages should fit
        assert len(with_tools) <= len(without_tools)

    def test_reserve_output_tokens(self, model_config):
        messages = [LLMMessage(role="user", content="x " * 100) for _ in range(10)]
        large_reserve = build_context("sys", messages, None, model_config, reserve_output=3000)
        small_reserve = build_context("sys", messages, None, model_config, reserve_output=100)
        assert len(large_reserve) <= len(small_reserve)


class TestEstimateToolsTokens:
    def test_no_tools(self):
        assert estimate_tools_tokens(None) == 0
        assert estimate_tools_tokens([]) == 0

    def test_with_tools(self):
        tools = [{"name": "shell", "description": "Run a command", "input_schema": {"type": "object"}}]
        tokens = estimate_tools_tokens(tools)
        assert tokens > 0


# --- DB pool tests (unit, no real DB) ---


class TestDBPool:
    def test_get_schema_default(self, monkeypatch):
        from inotagent.db.pool import get_schema
        monkeypatch.delenv("PLATFORM_SCHEMA", raising=False)
        assert get_schema() == "platform"

    def test_get_schema_custom(self, monkeypatch):
        from inotagent.db.pool import get_schema
        monkeypatch.setenv("PLATFORM_SCHEMA", "openvaia")
        assert get_schema() == "openvaia"

    async def test_get_connection_without_init_raises(self):
        from inotagent.db.pool import get_connection
        import inotagent.db.pool as pool_mod
        # Ensure pool is None
        old_pool = pool_mod._pool
        pool_mod._pool = None
        try:
            with pytest.raises(RuntimeError, match="not initialized"):
                async with get_connection():
                    pass
        finally:
            pool_mod._pool = old_pool

    async def test_close_pool_when_none(self):
        from inotagent.db.pool import close_pool
        import inotagent.db.pool as pool_mod
        old_pool = pool_mod._pool
        pool_mod._pool = None
        try:
            await close_pool()  # should not raise
        finally:
            pool_mod._pool = old_pool

    def test_build_conninfo(self, monkeypatch):
        from inotagent.db.pool import _build_conninfo
        monkeypatch.setenv("POSTGRES_HOST", "myhost")
        monkeypatch.setenv("POSTGRES_PORT", "5433")
        monkeypatch.setenv("POSTGRES_DB", "mydb")
        monkeypatch.setenv("POSTGRES_USER", "myuser")
        monkeypatch.setenv("POSTGRES_PASSWORD", "secret")
        info = _build_conninfo()
        assert "myhost" in info
        assert "5433" in info
        assert "mydb" in info
        assert "myuser" in info
        assert "secret" in info


# --- Conversation save/load logic tests (mocked DB) ---


class TestConversationLogic:
    def test_message_to_llm_message_mapping(self):
        """Verify the row-to-LLMMessage logic handles all fields."""
        # Simulate what load_history does with a row
        row = {
            "role": "assistant",
            "content": "I'll check that",
            "tool_calls": [{"id": "tc1", "name": "shell", "arguments": {"command": "ls"}}],
            "metadata": {"tool_call_id": None},
        }

        tc_data = row["tool_calls"]
        tool_calls = [ToolCall(id=tc["id"], name=tc["name"], arguments=tc["arguments"]) for tc in tc_data]
        msg = LLMMessage(
            role=row["role"],
            content=row["content"],
            tool_calls=tool_calls,
        )
        assert msg.role == "assistant"
        assert msg.tool_calls[0].name == "shell"

    def test_tool_message_with_call_id(self):
        row = {
            "role": "tool",
            "content": "file1.py\nfile2.py",
            "tool_calls": None,
            "metadata": {"tool_call_id": "tc1"},
        }
        meta = row["metadata"]
        msg = LLMMessage(
            role=row["role"],
            content=row["content"],
            tool_call_id=meta.get("tool_call_id"),
        )
        assert msg.role == "tool"
        assert msg.tool_call_id == "tc1"


# --- Memory DB module tests (mocked) ---


class TestMemoryModule:
    def test_max_memory_chars_constant(self):
        from inotagent.db.memory import MAX_MEMORY_CHARS
        assert MAX_MEMORY_CHARS == 8000

    async def test_get_embedding_no_client(self):
        """Returns None when embedding client is not initialized."""
        from inotagent.db.memory import _get_embedding
        with patch("inotagent.llm.embeddings._client", None):
            result = await _get_embedding("test text")
        assert result is None

    async def test_get_embedding_with_client(self):
        """Returns vector when embedding client is available."""
        from inotagent.db.memory import _get_embedding
        mock_client = AsyncMock()
        mock_client.embed_one.return_value = [0.1, 0.2, 0.3]
        with patch("inotagent.llm.embeddings._client", mock_client):
            result = await _get_embedding("test text", input_type="query")
        assert result == [0.1, 0.2, 0.3]
        mock_client.embed_one.assert_called_once_with("test text", input_type="query")

    async def test_get_embedding_handles_error(self):
        """Falls back to None on embedding API failure."""
        from inotagent.db.memory import _get_embedding
        mock_client = AsyncMock()
        mock_client.embed_one.side_effect = Exception("API error")
        with patch("inotagent.llm.embeddings._client", mock_client):
            result = await _get_embedding("test text")
        assert result is None


# --- Agent loop with persistence tests ---


class TestLoopPersistence:
    @pytest.fixture
    def model_config(self):
        return ModelConfig(
            id="test-model", provider="nvidia", model="test/model",
            api_key_env="X", base_url="http://x",
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

    async def test_run_without_db(self, agent_config, models):
        """Without DB, loop works in stateless mode."""
        loop = AgentLoop(config=agent_config, models=models, db_available=False)

        with patch("inotagent.loop.chat_with_fallback", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = LLMResponse(content="Hi!")
            result = await loop.run("hello")

        assert result == "Hi!"

    async def test_run_with_conversation_id_and_db(self, agent_config, models):
        """With conversation_id and DB, messages are saved."""
        loop = AgentLoop(config=agent_config, models=models, db_available=True)

        saved_messages = []

        async def mock_save(**kwargs):
            saved_messages.append(kwargs)

        async def mock_load(conversation_id, limit=100):
            return []

        with patch("inotagent.loop.chat_with_fallback", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = LLMResponse(content="Reply")
            with patch("inotagent.db.conversations.load_history", side_effect=mock_load):
                with patch("inotagent.db.conversations.save_message", side_effect=mock_save):
                    result = await loop.run("hello", conversation_id="conv-1", channel_type="discord")

        assert result == "Reply"
        # Should have saved user message + assistant response
        assert len(saved_messages) == 2
        assert saved_messages[0]["role"] == "user"
        assert saved_messages[0]["content"] == "hello"
        assert saved_messages[1]["role"] == "assistant"
        assert saved_messages[1]["content"] == "Reply"

    async def test_run_with_conv_id_loads_history(self, agent_config, models):
        """DB history is loaded and passed to LLM."""
        loop = AgentLoop(config=agent_config, models=models, db_available=True)

        db_history = [
            LLMMessage(role="user", content="previous question"),
            LLMMessage(role="assistant", content="previous answer"),
        ]

        with patch("inotagent.loop.chat_with_fallback", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = LLMResponse(content="Follow-up reply")
            with patch("inotagent.db.conversations.load_history", new_callable=AsyncMock) as mock_load:
                mock_load.return_value = db_history
                with patch("inotagent.db.conversations.save_message", new_callable=AsyncMock):
                    await loop.run("follow-up", conversation_id="conv-1")

        # Check that messages passed to LLM include DB history + new message
        call_kwargs = mock_chat.call_args[1]
        messages = call_kwargs["messages"]
        assert any(m.content == "previous question" for m in messages)
        assert messages[-1].content == "follow-up"

    async def test_run_without_conv_id_uses_local_history(self, agent_config, models):
        """Without conversation_id, uses provided history list."""
        loop = AgentLoop(config=agent_config, models=models, db_available=True)

        history = [LLMMessage(role="user", content="old")]

        with patch("inotagent.loop.chat_with_fallback", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = LLMResponse(content="ok")
            result = await loop.run("new", history=history)

        call_kwargs = mock_chat.call_args[1]
        messages = call_kwargs["messages"]
        assert messages[-1].content == "new"

    async def test_tool_calls_saved_to_db(self, agent_config, models):
        """Tool calls and results are saved to DB."""
        reg = ToolRegistry()
        reg.register("shell", AsyncMock(return_value="output"), {"name": "shell"})
        loop = AgentLoop(
            config=agent_config, models=models,
            tool_registry=reg, db_available=True,
        )

        saved = []

        async def mock_save(**kwargs):
            saved.append(kwargs)

        call_count = 0

        async def mock_chat(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return LLMResponse(
                    content="",
                    tool_calls=[ToolCall(id="tc1", name="shell", arguments={"command": "ls"})],
                )
            return LLMResponse(content="Done")

        with patch("inotagent.loop.chat_with_fallback", side_effect=mock_chat):
            with patch("inotagent.db.conversations.load_history", new_callable=AsyncMock, return_value=[]):
                with patch("inotagent.db.conversations.save_message", side_effect=mock_save):
                    await loop.run("list files", conversation_id="conv-1")

        roles = [s["role"] for s in saved]
        # user, assistant (with tool calls), tool result, assistant (final)
        assert roles == ["user", "assistant", "tool", "assistant"]
        # The assistant message should have tool_calls
        assert saved[1].get("tool_calls") is not None

    async def test_context_truncation_applied(self, agent_config, models):
        """Verify build_context is used to truncate messages."""
        # Use tiny context model
        tiny_model = ModelConfig(
            id="test-model", provider="nvidia", model="test/model",
            api_key_env="X", base_url="http://x",
            context_window=500, max_tokens=100,
        )
        loop = AgentLoop(
            config=agent_config, models={"test-model": tiny_model}, db_available=False,
        )

        # Create history that's too long for context
        long_history = [LLMMessage(role="user", content="x " * 200) for _ in range(20)]

        with patch("inotagent.loop.chat_with_fallback", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = LLMResponse(content="ok")
            await loop.run("latest", history=long_history)

        # Should have truncated — fewer messages than provided
        call_kwargs = mock_chat.call_args[1]
        messages = call_kwargs["messages"]
        assert len(messages) < len(long_history) + 1
        # Latest message should always be included
        assert messages[-1].content == "latest"


# --- Platform tool DB integration tests (mocked) ---


class TestPlatformToolsWithDB:
    async def test_task_list_no_db(self):
        from inotagent.tools.platform import PlatformTools
        pt = PlatformTools(agent_name="test", db_available=False)
        result = await pt.task_list()
        assert "not connected" in result.lower()

    async def test_task_list_with_db(self):
        from inotagent.tools.platform import PlatformTools
        pt = PlatformTools(agent_name="test", db_available=True)

        mock_rows = [
            {"key": "INO-001", "title": "Fix bug", "status": "todo",
             "priority": "high", "assigned_to": "robin", "created_by": "ino",
             "parent_key": "-"},
        ]

        mock_conn = AsyncMock()
        mock_cur = AsyncMock()
        mock_cur.fetchall.return_value = mock_rows
        mock_conn.execute.return_value = mock_cur
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)

        with patch("inotagent.db.pool.get_connection", return_value=mock_conn):
            with patch("inotagent.db.pool.get_schema", return_value="platform"):
                result = await pt.task_list(assigned_to="robin")

        assert "INO-001" in result
        assert "Fix bug" in result

    async def test_send_message_space_not_found(self):
        from inotagent.tools.platform import PlatformTools
        pt = PlatformTools(agent_name="test", db_available=True)

        mock_conn = AsyncMock()
        mock_cur = AsyncMock()
        mock_cur.fetchone.return_value = None
        mock_conn.execute.return_value = mock_cur
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)

        with patch("inotagent.db.pool.get_connection", return_value=mock_conn):
            with patch("inotagent.db.pool.get_schema", return_value="platform"):
                result = await pt.send_message(space_name="nonexistent", body="hi")

        assert "not found" in result.lower()


# --- Memory tool DB integration tests (mocked) ---


class TestMemoryToolsWithDB:
    async def test_memory_store_no_db(self):
        from inotagent.tools.memory import MemoryTools
        mt = MemoryTools(agent_name="test", db_available=False)
        result = await mt.memory_store(content="test", tags=["x"], tier="short")
        assert "not connected" in result.lower()

    async def test_memory_store_with_db(self):
        from inotagent.tools.memory import MemoryTools
        mt = MemoryTools(agent_name="test", db_available=True)

        with patch("inotagent.db.memory.store_memory", new_callable=AsyncMock):
            result = await mt.memory_store(content="remember this", tags=["pref"], tier="long")

        assert "long-term" in result
        assert "pref" in result

    async def test_memory_search_with_db_no_results(self):
        from inotagent.tools.memory import MemoryTools
        mt = MemoryTools(agent_name="test", db_available=True)

        with patch("inotagent.db.memory.search_memory", new_callable=AsyncMock, return_value=[]):
            result = await mt.memory_search(query="nothing")

        assert "No memories found" in result

    async def test_memory_search_with_db_has_results(self):
        from inotagent.tools.memory import MemoryTools
        mt = MemoryTools(agent_name="test", db_available=True)

        mock_results = [
            {"content": "Boss prefers small PRs", "tags": ["preference", "boss"],
             "tier": "long", "created_at": "2026-03-01"},
            {"content": "PR #42 needs fixes", "tags": ["pr"],
             "tier": "short", "created_at": "2026-03-15"},
        ]

        with patch("inotagent.db.memory.search_memory", new_callable=AsyncMock, return_value=mock_results):
            result = await mt.memory_search(tags=["preference"])

        assert "Boss prefers small PRs" in result
        assert "long:" in result


# --- Main entry point DB integration ---


class TestMainDBIntegration:
    async def test_try_init_db_failure(self):
        from inotagent.main import try_init_db

        with patch("inotagent.db.pool.init_pool", new_callable=AsyncMock, side_effect=Exception("no pg")):
            result = await try_init_db()

        assert result is False

    async def test_try_init_db_success(self):
        from inotagent.main import try_init_db

        with patch("inotagent.db.pool.init_pool", new_callable=AsyncMock):
            result = await try_init_db()

        assert result is True
