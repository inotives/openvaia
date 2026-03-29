"""Project integrity tests — validates file existence, path consistency, config correctness.

Validates project structure, path consistency, and config correctness.
"""

import os
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parent.parent
AGENTS = [d.name for d in (ROOT / "agents").iterdir() if d.is_dir() and not d.name.startswith("_")]
WORKSPACE_PATH = "/workspace"


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------

class TestFileExistence:
    """Ensure all required project files exist."""

    @pytest.mark.parametrize("path", [
        "inotagent/platform.yml",
        "inotagent/models.yml",
        "inotagent/Dockerfile",
        "inotagent/entrypoint.sh",
        "inotagent/pyproject.toml",
        "inotagent/src/inotagent/__init__.py",
        "inotagent/src/inotagent/main.py",
        "inotagent/src/inotagent/loop.py",
        "inotagent/src/inotagent/bootstrap.py",
        "docker-compose.yml",
        "Makefile",
        "pyproject.toml",
        ".env.template",
        ".gitignore",
        "CLAUDE.md",
        "scripts/schema_dev.sh",
        "docs/project_summary.md",
    ])
    def test_core_files_exist(self, path):
        assert (ROOT / path).exists(), f"Missing: {path}"

    def test_migrations_exist(self):
        migrations = list((ROOT / "infra/postgres/migrations").glob("*.sql"))
        assert len(migrations) > 0, "No migration files found"

    @pytest.mark.parametrize("agent", AGENTS)
    def test_agent_workspace_files(self, agent):
        required = ["AGENTS.md", "TOOLS.md"]
        for f in required:
            assert (ROOT / f"agents/{agent}/{f}").exists(), f"Missing: agents/{agent}/{f}"

    @pytest.mark.parametrize("agent", AGENTS)
    def test_agent_config_files(self, agent):
        required = ["agent.yml", "Dockerfile", ".env.template"]
        for f in required:
            assert (ROOT / f"agents/{agent}/{f}").exists(), f"Missing: agents/{agent}/{f}"


# ---------------------------------------------------------------------------
# Path consistency
# ---------------------------------------------------------------------------

class TestPathConsistency:
    """Ensure workspace paths are consistent across all files."""

    def test_no_old_workspace_path_in_dockerfiles(self):
        """No references to /app/workspace or old OpenClaw workspace path."""
        for agent in AGENTS:
            content = (ROOT / f"agents/{agent}/Dockerfile").read_text()
            assert "/app/workspace" not in content, f"agents/{agent}/Dockerfile still uses /app/workspace"
            assert "/home/node/.openclaw/workspace" not in content, \
                f"agents/{agent}/Dockerfile still uses old OpenClaw workspace path"

    @pytest.mark.parametrize("agent", AGENTS)
    def test_tools_md_workspace_path(self, agent):
        content = (ROOT / f"agents/{agent}/TOOLS.md").read_text()
        assert WORKSPACE_PATH in content, f"agents/{agent}/TOOLS.md has wrong workspace path"

    def test_inotagent_dockerfile_workspace(self):
        content = (ROOT / "inotagent/Dockerfile").read_text()
        assert WORKSPACE_PATH in content, f"inotagent/Dockerfile missing {WORKSPACE_PATH}"


# ---------------------------------------------------------------------------
# Environment variable consistency
# ---------------------------------------------------------------------------

class TestEnvVarConsistency:
    """Ensure environment variables are named consistently."""

    def test_google_gemini_key_in_models(self):
        content = (ROOT / "inotagent/models.yml").read_text()
        assert "GOOGLE_GEMINI_API_KEY" in content, "models.yml should use GOOGLE_GEMINI_API_KEY"
        assert "GOOGLE_API_KEY" not in content, "models.yml should not use GOOGLE_API_KEY (use GOOGLE_GEMINI_API_KEY)"

    @pytest.mark.parametrize("agent", AGENTS)
    def test_google_gemini_key_in_env_template(self, agent):
        content = (ROOT / f"agents/{agent}/.env.template").read_text()
        assert "GOOGLE_GEMINI_API_KEY" in content, f"agents/{agent}/.env.template should use GOOGLE_GEMINI_API_KEY"

    def test_db_name_in_env_template(self):
        content = (ROOT / ".env.template").read_text()
        assert "POSTGRES_DB=inotives" in content, ".env.template should use POSTGRES_DB=inotives"

    def test_platform_schema_in_env_template(self):
        content = (ROOT / ".env.template").read_text()
        assert "PLATFORM_SCHEMA=" in content, ".env.template should define PLATFORM_SCHEMA"


# ---------------------------------------------------------------------------
# Config consistency
# ---------------------------------------------------------------------------

class TestConfigConsistency:
    """Ensure YAML configs are valid and consistent."""

    def test_platform_yml_valid(self):
        data = yaml.safe_load((ROOT / "inotagent/platform.yml").read_text())
        assert "llm" in data
        assert "default_model" in data["llm"]

    def test_models_yml_valid(self):
        data = yaml.safe_load((ROOT / "inotagent/models.yml").read_text())
        assert "models" in data
        assert len(data["models"]) > 0
        for model in data["models"]:
            assert "id" in model, f"Model missing 'id': {model}"
            assert "provider" in model, f"Model missing 'provider': {model}"
            assert "model" in model, f"Model missing 'model': {model}"

    def test_default_model_exists_in_registry(self):
        platform = yaml.safe_load((ROOT / "inotagent/platform.yml").read_text())
        models = yaml.safe_load((ROOT / "inotagent/models.yml").read_text())
        default = platform["llm"]["default_model"]
        model_ids = [m["id"] for m in models["models"]]
        assert default in model_ids, f"Default model '{default}' not found in models.yml"

    @pytest.mark.parametrize("agent", AGENTS)
    def test_agent_model_exists_in_registry(self, agent):
        agent_config = yaml.safe_load((ROOT / f"agents/{agent}/agent.yml").read_text())
        if "model" in agent_config:
            models = yaml.safe_load((ROOT / "inotagent/models.yml").read_text())
            model_ids = [m["id"] for m in models["models"]]
            assert agent_config["model"] in model_ids, \
                f"Agent '{agent}' model '{agent_config['model']}' not found in models.yml"

    @pytest.mark.parametrize("agent", AGENTS)
    def test_agent_yml_valid(self, agent):
        data = yaml.safe_load((ROOT / f"agents/{agent}/agent.yml").read_text())
        assert isinstance(data, dict), f"agents/{agent}/agent.yml is not valid YAML"


# ---------------------------------------------------------------------------
# Docker compose
# ---------------------------------------------------------------------------

class TestDockerCompose:
    """Validate docker-compose.yml structure."""

    def _load(self):
        return yaml.safe_load((ROOT / "docker-compose.yml").read_text())

    def test_postgres_has_infra_profile(self):
        data = self._load()
        pg = data["services"]["postgres"]
        assert "profiles" in pg, "postgres service missing profiles"
        assert "infra" in pg["profiles"], "postgres service should have 'infra' profile"

    def test_agents_use_env_var_for_postgres_host(self):
        data = self._load()
        for agent in AGENTS:
            if agent in data["services"]:
                env = data["services"][agent].get("environment", {})
                if "POSTGRES_HOST" in env:
                    val = str(env["POSTGRES_HOST"])
                    assert "${" in val, f"{agent} POSTGRES_HOST should use env var substitution, got: {val}"

    @pytest.mark.parametrize("agent", AGENTS)
    def test_agent_service_exists(self, agent):
        data = self._load()
        assert agent in data["services"], f"Agent '{agent}' missing from docker-compose.yml"

    @pytest.mark.parametrize("agent", AGENTS)
    def test_agent_dockerfile_reference(self, agent):
        data = self._load()
        svc = data["services"][agent]
        expected = f"agents/{agent}/Dockerfile"
        assert svc["build"]["dockerfile"] == expected, \
            f"{agent} service references wrong Dockerfile: {svc['build']['dockerfile']}"

    def test_platform_network_exists(self):
        data = self._load()
        assert "platform" in data.get("networks", {}), "Missing 'platform' network"


# ---------------------------------------------------------------------------
# Dockerfile validation
# ---------------------------------------------------------------------------

class TestDockerfiles:
    """Validate Dockerfile structure."""

    def test_base_image_is_python(self):
        content = (ROOT / "inotagent/Dockerfile").read_text()
        first_line = content.strip().split("\n")[0]
        assert "python:3.12" in first_line, "inotagent/Dockerfile should use python:3.12 base image"

    def test_base_copies_core_config(self):
        content = (ROOT / "inotagent/Dockerfile").read_text()
        required_copies = [
            "inotagent/models.yml",
            "inotagent/platform.yml",
            "infra/postgres/migrations",
        ]
        for path in required_copies:
            assert path in content, f"inotagent/Dockerfile missing COPY for {path}"

    def test_base_copies_inotagent_source(self):
        content = (ROOT / "inotagent/Dockerfile").read_text()
        assert "inotagent/src/" in content, "inotagent/Dockerfile missing COPY for inotagent source"

    @pytest.mark.parametrize("agent", AGENTS)
    def test_agent_dockerfile_copies_workspace_files(self, agent):
        content = (ROOT / f"agents/{agent}/Dockerfile").read_text()
        required = ["AGENTS.md", "TOOLS.md"]
        for f in required:
            assert f in content, f"agents/{agent}/Dockerfile missing COPY for {f}"

    @pytest.mark.parametrize("agent", AGENTS)
    def test_agent_dockerfile_copies_agent_yml(self, agent):
        content = (ROOT / f"agents/{agent}/Dockerfile").read_text()
        assert "agent.yml" in content, f"agents/{agent}/Dockerfile missing COPY for agent.yml"

    @pytest.mark.parametrize("agent", AGENTS)
    def test_agent_dockerfile_extends_base(self, agent):
        content = (ROOT / f"agents/{agent}/Dockerfile").read_text()
        first_line = content.strip().split("\n")[0]
        assert "inotagent-base" in first_line, f"agents/{agent}/Dockerfile should extend inotagent-base"


# ---------------------------------------------------------------------------
# Entrypoint validation
# ---------------------------------------------------------------------------

class TestEntrypoint:
    """Validate boot sequence in inotagent entrypoint.sh."""

    def _content(self):
        return (ROOT / "inotagent/entrypoint.sh").read_text()

    def test_creates_database(self):
        assert "CREATE DATABASE" in self._content(), "Entrypoint should create database if not exists"

    def test_runs_dbmate_migrations(self):
        assert "dbmate" in self._content(), "Entrypoint should run dbmate migrations"

    def test_runs_bootstrap(self):
        assert "inotagent.bootstrap" in self._content(), "Entrypoint should run bootstrap"

    def test_starts_inotagent(self):
        assert "python3 -m inotagent" in self._content(), "Entrypoint should start inotagent"

    def test_inotagent_is_exec(self):
        """inotagent should be exec'd (PID 1)."""
        assert "exec python3 -m inotagent" in self._content(), "inotagent should be exec'd as PID 1"


# ---------------------------------------------------------------------------
# Migration validation
# ---------------------------------------------------------------------------

class TestMigrations:
    """Validate database migration files."""

    def test_init_sql_removed(self):
        assert not (ROOT / "infra/postgres/init.sql").exists(), "init.sql should be removed (replaced by dbmate)"

    def test_migration_has_up_and_down(self):
        for f in (ROOT / "infra/postgres/migrations").glob("*.sql"):
            content = f.read_text()
            assert "-- migrate:up" in content, f"{f.name} missing '-- migrate:up'"
            assert "-- migrate:down" in content, f"{f.name} missing '-- migrate:down'"

    def test_migration_creates_platform_schema(self):
        migrations = list((ROOT / "infra/postgres/migrations").glob("*.sql"))
        all_content = " ".join(f.read_text() for f in migrations)
        assert "CREATE SCHEMA" in all_content, "Migrations should create platform schema"

    def test_migration_creates_required_tables(self):
        migrations = list((ROOT / "infra/postgres/migrations").glob("*.sql"))
        all_content = " ".join(f.read_text() for f in migrations)
        required_tables = ["platform.spaces", "platform.messages", "platform.agents",
                           "platform.agent_status", "platform.config", "platform.agent_repos"]
        for table in required_tables:
            assert table in all_content, f"Migrations should create {table}"

    def test_migration_seeds_public_space(self):
        migrations = list((ROOT / "infra/postgres/migrations").glob("*.sql"))
        all_content = " ".join(f.read_text() for f in migrations)
        assert "'public'" in all_content, "Migrations should seed the public space"


# ---------------------------------------------------------------------------
# Gitignore
# ---------------------------------------------------------------------------

class TestGitignore:
    """Ensure sensitive files are gitignored."""

    def _content(self):
        return (ROOT / ".gitignore").read_text()

    def test_root_env_ignored(self):
        assert ".env" in self._content(), ".gitignore should exclude .env"

    def test_agent_env_ignored(self):
        assert "agents/*/.env" in self._content(), ".gitignore should exclude agents/*/.env"

    def test_backups_ignored(self):
        assert "backups" in self._content(), ".gitignore should exclude backups"

    def test_pycache_ignored(self):
        assert "__pycache__" in self._content(), ".gitignore should exclude __pycache__"

    def test_venv_ignored(self):
        assert ".venv" in self._content(), ".gitignore should exclude .venv"


# ---------------------------------------------------------------------------
# Makefile
# ---------------------------------------------------------------------------

class TestMakefile:
    """Ensure all expected Makefile targets exist."""

    def _content(self):
        return (ROOT / "Makefile").read_text()

    @pytest.mark.parametrize("target", [
        "build-base", "build", "deploy", "deploy-all",
        "start", "stop", "restart", "down", "ps", "logs",
        "shell", "bootstrap",
        "task-list", "task-get", "task-create", "task-update",
        "task-summary", "task-board",
        "repo-list", "repo-add", "repo-remove", "repo-agent",
        "test", "inotagent-test",
    ])
    def test_target_exists(self, target):
        content = self._content()
        assert f"{target}:" in content, f"Makefile missing target: {target}"


# ---------------------------------------------------------------------------
# inotagent module structure
# ---------------------------------------------------------------------------

class TestInotagentStructure:
    """Validate inotagent package structure."""

    @pytest.mark.parametrize("module", [
        "llm",
        "tools",
        "channels",
        "db",
        "scheduler",
        "config",
    ])
    def test_subpackages_exist(self, module):
        pkg = ROOT / f"inotagent/src/inotagent/{module}"
        assert pkg.is_dir(), f"Missing package: inotagent/{module}"
        assert (pkg / "__init__.py").exists(), f"Missing __init__.py in inotagent/{module}"

    def test_tests_directory_exists(self):
        assert (ROOT / "inotagent/tests").is_dir(), "Missing inotagent/tests"
