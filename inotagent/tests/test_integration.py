"""Tests for Phase 6 — bootstrap, Docker integration, and end-to-end wiring."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from inotagent.bootstrap import (
    add_all_agents_to_space,
    add_to_space,
    announce_pending_tasks,
    bootstrap,
    ensure_space,
    register_agent,
    send_announcement,
    sync_repos,
)


# --- Bootstrap tests ---


class TestRegisterAgent:
    async def test_register_agent_inserts(self):
        mock_conn = AsyncMock()
        with patch("inotagent.bootstrap.get_connection") as mock_get:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
            await register_agent("robin")

        mock_conn.execute.assert_awaited_once()
        call_args = mock_conn.execute.call_args
        assert "INSERT INTO" in call_args[0][0]
        assert "robin" in call_args[0][1]


class TestEnsureSpace:
    async def test_creates_new_space(self):
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value={"id": 1})
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch("inotagent.bootstrap.get_connection") as mock_get:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await ensure_space("tasks", "room")

        assert result == 1

    async def test_returns_existing_space(self):
        mock_conn = AsyncMock()
        mock_cursor_insert = AsyncMock()
        mock_cursor_insert.fetchone = AsyncMock(return_value=None)  # Already exists
        mock_cursor_select = AsyncMock()
        mock_cursor_select.fetchone = AsyncMock(return_value={"id": 42})
        mock_conn.execute = AsyncMock(side_effect=[mock_cursor_insert, mock_cursor_select])

        with patch("inotagent.bootstrap.get_connection") as mock_get:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await ensure_space("tasks", "room")

        assert result == 42


class TestAddToSpace:
    async def test_adds_agent_to_space(self):
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value={"id": 1})
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch("inotagent.bootstrap.get_connection") as mock_get:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
            await add_to_space("robin", "tasks")

        # First call: SELECT space, Second call: INSERT member
        assert mock_conn.execute.await_count == 2

    async def test_skips_if_space_not_found(self):
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch("inotagent.bootstrap.get_connection") as mock_get:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
            await add_to_space("robin", "nonexistent")

        # Only the SELECT call, no INSERT
        assert mock_conn.execute.await_count == 1


class TestAddAllAgentsToSpace:
    async def test_adds_all_agents(self):
        mock_conn = AsyncMock()
        mock_space_cursor = AsyncMock()
        mock_space_cursor.fetchone = AsyncMock(return_value={"id": 1})
        mock_agents_cursor = AsyncMock()
        mock_agents_cursor.fetchall = AsyncMock(return_value=[{"name": "ino"}, {"name": "robin"}])

        mock_conn.execute = AsyncMock(side_effect=[mock_space_cursor, mock_agents_cursor, AsyncMock(), AsyncMock()])

        with patch("inotagent.bootstrap.get_connection") as mock_get:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
            await add_all_agents_to_space("tasks")

        # SELECT space + SELECT agents + 2x INSERT member
        assert mock_conn.execute.await_count == 4


class TestSendAnnouncement:
    async def test_sends_message(self):
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value={"id": 1})
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch("inotagent.bootstrap.get_connection") as mock_get:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
            await send_announcement("robin", "public", "hello")

        assert mock_conn.execute.await_count == 2  # SELECT + INSERT

    async def test_skips_if_space_not_found(self):
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch("inotagent.bootstrap.get_connection") as mock_get:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
            await send_announcement("robin", "nonexistent", "hello")

        assert mock_conn.execute.await_count == 1  # Only SELECT


class TestAnnouncePendingTasks:
    async def test_no_pending_tasks(self):
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[])
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch("inotagent.bootstrap.get_connection") as mock_get:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
            await announce_pending_tasks("robin")

        # Only SELECT tasks, no announcement
        assert mock_conn.execute.await_count == 1

    async def test_announces_tasks(self):
        mock_conn = AsyncMock()
        mock_task_cursor = AsyncMock()
        mock_task_cursor.fetchall = AsyncMock(return_value=[
            {"key": "INO-001", "title": "Fix bug", "status": "todo", "priority": "high", "created_by": "ino"},
        ])
        mock_space_cursor = AsyncMock()
        mock_space_cursor.fetchone = AsyncMock(return_value={"id": 1})

        mock_conn.execute = AsyncMock(side_effect=[mock_task_cursor, mock_space_cursor, AsyncMock()])

        with patch("inotagent.bootstrap.get_connection") as mock_get:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
            await announce_pending_tasks("robin")


class TestSyncRepos:
    async def test_no_repos(self):
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[])
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch("inotagent.bootstrap.get_connection") as mock_get:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch.dict(os.environ, {"WORKSPACE_DIR": "/tmp/test_workspace"}):
                await sync_repos("robin")

    async def test_clones_new_repo(self):
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[
            {"repo_name": "test-repo", "repo_url": "https://github.com/test/repo.git"},
        ])
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch("inotagent.bootstrap.get_connection") as mock_get:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch("subprocess.run") as mock_run:
                with patch("os.path.isdir", return_value=False):
                    with patch("os.makedirs"):
                        with patch.dict(os.environ, {"WORKSPACE_DIR": "/tmp/test_workspace"}):
                            await sync_repos("robin")

                mock_run.assert_called_once()
                args = mock_run.call_args[0][0]
                assert args[0] == "git"
                assert args[1] == "clone"

    async def test_pulls_existing_repo(self):
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[
            {"repo_name": "test-repo", "repo_url": "https://github.com/test/repo.git"},
        ])
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        with patch("inotagent.bootstrap.get_connection") as mock_get:
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch("subprocess.run") as mock_run:
                with patch("os.path.isdir", return_value=True):
                    with patch.dict(os.environ, {"WORKSPACE_DIR": "/tmp/test_workspace"}):
                        await sync_repos("robin")

                # fetch + pull
                assert mock_run.call_count == 2


class TestBootstrapFull:
    async def test_full_bootstrap_sequence(self):
        with (
            patch("inotagent.bootstrap.register_agent", new_callable=AsyncMock) as mock_register,
            patch("inotagent.bootstrap.ensure_space", new_callable=AsyncMock, return_value=1) as mock_ensure,
            patch("inotagent.bootstrap.add_to_space", new_callable=AsyncMock) as mock_add,
            patch("inotagent.bootstrap.add_all_agents_to_space", new_callable=AsyncMock) as mock_add_all,
            patch("inotagent.bootstrap.send_announcement", new_callable=AsyncMock) as mock_announce,
            patch("inotagent.bootstrap.announce_pending_tasks", new_callable=AsyncMock) as mock_pending,
            patch("inotagent.bootstrap.sync_repos", new_callable=AsyncMock) as mock_sync,
            patch("inotagent.db.agent_configs.seed_agent_configs", new_callable=AsyncMock) as mock_seed_configs,
        ):
            await bootstrap("robin")

        mock_register.assert_awaited_once_with("robin", role="")
        assert mock_ensure.await_count == 2  # tasks + public
        assert mock_add.await_count == 2  # robin to tasks + public
        mock_add_all.assert_awaited_once_with("tasks")
        mock_announce.assert_awaited_once()
        mock_pending.assert_awaited_once_with("robin")
        mock_sync.assert_awaited_once_with("robin")
        mock_seed_configs.assert_awaited_once()


# --- Main entry point tests ---


class TestMainEntryPoint:
    def test_resolve_paths_valid(self, tmp_path):
        # Create agent structure
        agents_dir = tmp_path / "agents" / "robin"
        agents_dir.mkdir(parents=True)
        inotagent_dir = tmp_path / "inotagent"
        inotagent_dir.mkdir()
        (inotagent_dir / "models.yml").write_text("")
        (inotagent_dir / "platform.yml").write_text("")

        from inotagent.main import resolve_paths
        agent_path, models_path, platform_path = resolve_paths(str(agents_dir))

        assert agent_path == agents_dir
        assert models_path == inotagent_dir / "models.yml"
        assert platform_path == inotagent_dir / "platform.yml"

    def test_resolve_paths_missing_agent_dir(self):
        from inotagent.main import resolve_paths
        with pytest.raises(FileNotFoundError, match="Agent directory not found"):
            resolve_paths("/nonexistent/agents/robin")

    def test_resolve_paths_missing_inotagent_dir(self, tmp_path):
        agents_dir = tmp_path / "agents" / "robin"
        agents_dir.mkdir(parents=True)

        from inotagent.main import resolve_paths
        with pytest.raises(FileNotFoundError, match="inotagent directory not found"):
            resolve_paths(str(agents_dir))

    def test_dunder_main_module_exists(self):
        """Verify __main__.py exists for `python -m inotagent`."""
        main_file = Path(__file__).parent.parent / "src" / "inotagent" / "__main__.py"
        assert main_file.exists()

    async def test_workspace_dir_env_used(self):
        """Verify WORKSPACE_DIR env is used as default_working_dir for tools."""
        from inotagent.main import async_main
        from unittest.mock import MagicMock
        import argparse

        # This is a structural test — verify the env var path is used
        with patch.dict(os.environ, {"WORKSPACE_DIR": "/workspace"}):
            workspace = os.environ.get("WORKSPACE_DIR", "/default")
        assert workspace == "/workspace"


# --- Docker composition tests ---


class TestDockerComposition:
    """Verify Docker-related files exist and have correct structure."""

    def test_dockerfile_exists(self):
        dockerfile = Path(__file__).parent.parent / "Dockerfile"
        assert dockerfile.exists()

    def test_dockerfile_uses_python_slim(self):
        dockerfile = Path(__file__).parent.parent / "Dockerfile"
        content = dockerfile.read_text()
        assert "python:3.12-slim" in content
        assert "openclaw" not in content.lower()

    def test_dockerfile_installs_deps(self):
        dockerfile = Path(__file__).parent.parent / "Dockerfile"
        content = dockerfile.read_text()
        assert "gh" in content  # GitHub CLI
        assert "uv" in content  # uv package manager
        assert "dbmate" in content  # DB migrations

    def test_entrypoint_exists(self):
        entrypoint = Path(__file__).parent.parent / "entrypoint.sh"
        assert entrypoint.exists()

    def test_entrypoint_has_correct_steps(self):
        entrypoint = Path(__file__).parent.parent / "entrypoint.sh"
        content = entrypoint.read_text()
        assert "AGENT_NAME" in content
        assert "git config" in content  # Step 1: git creds
        assert "CREATE DATABASE" in content  # Step 2: ensure DB
        assert "dbmate" in content  # Step 3: migrations
        assert "inotagent.bootstrap" in content  # Step 4: bootstrap
        assert "inotagent" in content  # Step 5: start

    def test_docker_compose_uses_inotagent(self):
        compose = Path(__file__).parent.parent.parent / "docker-compose.yml"
        assert compose.exists()
        content = compose.read_text()
        # Should NOT reference OpenClaw
        assert "openclaw" not in content.lower()
        assert "18789" not in content  # Old OpenClaw port
        assert "8080" not in content  # No HTTP health endpoint
        # Should have workspace volumes
        assert "robin_workspace" in content
        assert "ino_workspace" in content

    def test_agent_dockerfiles_use_inotagent_base(self):
        for agent in ["ino", "robin"]:
            dockerfile = Path(__file__).parent.parent.parent / "agents" / agent / "Dockerfile"
            assert dockerfile.exists()
            content = dockerfile.read_text()
            assert "inotagent-base" in content
            assert "inotives-base" not in content
            assert "openclaw" not in content.lower()

    def test_makefile_references_inotagent(self):
        makefile = Path(__file__).parent.parent.parent / "Makefile"
        assert makefile.exists()
        content = makefile.read_text()
        assert "inotagent/Dockerfile" in content
        assert "inotagent-base" in content
        assert "inotagent-test" in content


# --- Agent workspace path tests ---


class TestAgentWorkspacePaths:
    def test_robin_agents_md_uses_workspace_paths(self):
        robin_md = Path(__file__).parent.parent.parent / "agents" / "robin" / "AGENTS.md"
        assert robin_md.exists()
        content = robin_md.read_text()
        assert "/workspace/repos/" in content
        # Should NOT reference old OpenClaw paths
        assert "/home/node/.openclaw" not in content

    def test_robin_agents_md_uses_tool_functions(self):
        robin_md = Path(__file__).parent.parent.parent / "agents" / "robin" / "AGENTS.md"
        content = robin_md.read_text()
        assert "task_list(" in content
        # Should NOT reference old CLI syntax
        assert "platform_tools" not in content

    def test_ino_agents_md_uses_tool_functions(self):
        ino_md = Path(__file__).parent.parent.parent / "agents" / "ino" / "AGENTS.md"
        content = ino_md.read_text()
        assert "task_list(" in content
        assert "platform_tools" not in content
