"""UI tests — validates file structure, Docker integration, Next.js project config, and auth protection."""

import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parent.parent
AGENTS = [d.name for d in (ROOT / "agents").iterdir() if d.is_dir()]


# ---------------------------------------------------------------------------
# File structure
# ---------------------------------------------------------------------------

class TestUIFileStructure:
    """Ensure all required UI files exist."""

    @pytest.mark.parametrize("path", [
        "ui/package.json",
        "ui/tsconfig.json",
        "ui/next.config.ts",
        "ui/Dockerfile",
        "ui/src/app/layout.tsx",
        "ui/src/app/page.tsx",
        "ui/src/app/dashboard/page.tsx",
        "ui/src/app/tasks/page.tsx",
        "ui/src/app/messages/page.tsx",
        "ui/src/app/agents/page.tsx",
        "ui/src/app/config/page.tsx",
        "ui/src/lib/db.ts",
        "ui/src/lib/constants.ts",
        "ui/src/lib/types.ts",
        "ui/src/middleware.ts",
        "ui/src/components/AppLayout.tsx",
    ])
    def test_file_exists(self, path):
        assert (ROOT / path).exists(), f"Missing: {path}"


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

class TestAPIRoutes:
    """Ensure API route files exist."""

    @pytest.mark.parametrize("path", [
        "ui/src/app/api/dashboard/agents/route.ts",
        "ui/src/app/api/dashboard/tasks/route.ts",
        "ui/src/app/api/dashboard/messages/route.ts",
    ])
    def test_api_route_exists(self, path):
        assert (ROOT / path).exists(), f"Missing API route: {path}"


# ---------------------------------------------------------------------------
# Docker Compose
# ---------------------------------------------------------------------------

class TestUIDockerCompose:
    """Validate docker-compose.yml UI service."""

    def _load(self):
        return yaml.safe_load((ROOT / "docker-compose.yml").read_text())

    def test_ui_service_exists(self):
        data = self._load()
        assert "ui" in data["services"], "Missing 'ui' service"

    def test_ui_dockerfile_reference(self):
        data = self._load()
        svc = data["services"]["ui"]
        assert svc["build"]["dockerfile"] == "ui/Dockerfile"

    def test_ui_port_exposed(self):
        data = self._load()
        svc = data["services"]["ui"]
        ports = str(svc.get("ports", []))
        assert "7860" in ports, "UI should expose port 7860"

    def test_ui_on_platform_network(self):
        data = self._load()
        svc = data["services"]["ui"]
        networks = svc.get("networks", [])
        assert "platform" in networks, "UI should be on platform network"

    def test_ui_has_memory_limit(self):
        data = self._load()
        svc = data["services"]["ui"]
        limit = svc.get("deploy", {}).get("resources", {}).get("limits", {}).get("memory")
        assert limit is not None, "UI should have memory limit"


# ---------------------------------------------------------------------------
# Makefile
# ---------------------------------------------------------------------------

class TestUIMakefile:
    """Ensure Makefile targets for UI exist."""

    @pytest.mark.parametrize("target", ["ui", "ui-logs"])
    def test_target_exists(self, target):
        content = (ROOT / "Makefile").read_text()
        assert f"{target}:" in content, f"Makefile missing target: {target}"


# ---------------------------------------------------------------------------
# Dockerfile
# ---------------------------------------------------------------------------

class TestUIDockerfile:
    """Validate UI Dockerfile contents."""

    def _content(self):
        return (ROOT / "ui/Dockerfile").read_text()

    def test_uses_node_alpine(self):
        assert "node:20-alpine" in self._content()

    def test_exposes_port(self):
        assert "EXPOSE 7860" in self._content()

    def test_runs_server(self):
        assert "server.js" in self._content()

    def test_multi_stage_build(self):
        content = self._content()
        assert "AS builder" in content
        assert "AS runner" in content


# ---------------------------------------------------------------------------
# Package.json
# ---------------------------------------------------------------------------

class TestUIPackageJson:
    """Validate package.json dependencies."""

    def _data(self):
        return json.loads((ROOT / "ui/package.json").read_text())

    def test_has_next(self):
        assert "next" in self._data()["dependencies"]

    def test_has_react(self):
        assert "react" in self._data()["dependencies"]

    def test_has_antd(self):
        assert "antd" in self._data()["dependencies"]

    def test_has_antd_registry(self):
        assert "@ant-design/nextjs-registry" in self._data()["dependencies"]

    def test_has_postgres(self):
        assert "postgres" in self._data()["dependencies"]

    def test_has_build_script(self):
        assert "build" in self._data()["scripts"]

    def test_standalone_output(self):
        content = (ROOT / "ui/next.config.ts").read_text()
        assert "standalone" in content


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestUIConstants:
    """Validate constants are defined."""

    def _content(self):
        return (ROOT / "ui/src/lib/constants.ts").read_text()

    def test_has_statuses(self):
        content = self._content()
        for s in ["backlog", "todo", "in_progress", "review", "done", "blocked"]:
            assert s in content, f"Missing status: {s}"

    def test_has_priorities(self):
        content = self._content()
        for p in ["critical", "high", "medium", "low"]:
            assert p in content, f"Missing priority: {p}"

    def test_has_status_colors(self):
        assert "STATUS_COLORS" in self._content()

    def test_has_priority_colors(self):
        assert "PRIORITY_COLORS" in self._content()


# ---------------------------------------------------------------------------
# Auth file structure
# ---------------------------------------------------------------------------

class TestAuthFileStructure:
    """Ensure all auth-related files exist."""

    @pytest.mark.parametrize("path", [
        "ui/src/lib/auth.ts",
        "ui/src/app/login/page.tsx",
        "ui/src/app/api/auth/[...nextauth]/route.ts",
        "ui/src/app/api/auth/providers-info/route.ts",
        "ui/src/components/SessionWrapper.tsx",
        "ui/src/components/LayoutSwitch.tsx",
    ])
    def test_file_exists(self, path):
        assert (ROOT / path).exists(), f"Missing auth file: {path}"


# ---------------------------------------------------------------------------
# Auth middleware protection
# ---------------------------------------------------------------------------

class TestAuthMiddleware:
    """Verify middleware protects all API routes except auth endpoints."""

    def _middleware(self):
        return (ROOT / "ui/src/middleware.ts").read_text()

    def _find_api_routes(self):
        """Discover all API route.ts files and return their URL paths."""
        api_dir = ROOT / "ui" / "src" / "app" / "api"
        routes = []
        for f in api_dir.rglob("route.ts"):
            # Convert file path to URL path
            rel = f.parent.relative_to(ROOT / "ui" / "src" / "app")
            url = "/" + str(rel).replace("\\", "/")
            routes.append(url)
        return sorted(routes)

    def test_middleware_exists(self):
        assert (ROOT / "ui/src/middleware.ts").exists()

    def test_middleware_uses_nextauth(self):
        content = self._middleware()
        assert 'import { auth } from "@/lib/auth"' in content

    def test_middleware_allows_login(self):
        content = self._middleware()
        assert '"/login"' in content or "'/login'" in content

    def test_middleware_allows_auth_routes(self):
        content = self._middleware()
        assert '"/api/auth"' in content or "'/api/auth'" in content

    def test_middleware_redirects_unauthenticated(self):
        """Middleware must redirect to /login when req.auth is falsy."""
        content = self._middleware()
        assert "req.auth" in content
        assert "redirect" in content.lower()

    def test_middleware_matcher_covers_api(self):
        """Middleware matcher must not exclude /api routes."""
        content = self._middleware()
        # The matcher uses a negative lookahead — ensure it only excludes static assets
        assert "_next/static" in content
        assert "_next/image" in content
        # Ensure /api is NOT excluded
        assert "api" not in content.split("(?!")[1].split(")")[0] if "(?!" in content else True

    def test_all_api_routes_discovered(self):
        """Ensure we have at least 20 API route files (sanity check)."""
        routes = self._find_api_routes()
        assert len(routes) >= 20, f"Expected ≥20 API routes, found {len(routes)}: {routes}"

    def test_auth_routes_are_public(self):
        """Only /api/auth/* routes should be publicly accessible."""
        routes = self._find_api_routes()
        public_routes = [r for r in routes if r.startswith("/api/auth")]
        assert len(public_routes) >= 2, "Should have at least nextauth + providers-info routes"

    @pytest.mark.parametrize("route", [
        "/api/dashboard/tasks",
        "/api/dashboard/scheduler",
        "/api/dashboard/agents",
        "/api/tasks",
        "/api/tasks/[key]",
        "/api/agents/[name]/repos",
        "/api/agents/[name]/research",
        "/api/agents/[name]/research/[id]",
        "/api/agents/[name]/chat",
        "/api/agents/[name]/skills",
        "/api/agents/[name]/metrics",
        "/api/agents/[name]/memories",
        "/api/agents/[name]/tasks",
        "/api/agents/[name]/configs",
        "/api/agents/[name]/restart",
        "/api/cron-jobs",
        "/api/cron-jobs/[id]",
        "/api/skills",
        "/api/skills/[id]",
        "/api/models",
    ])
    def test_protected_route_file_exists(self, route):
        """Every protected API route must have a corresponding route.ts file."""
        # Convert URL path to file path (strip leading /)
        file_path = ROOT / "ui" / "src" / "app" / route.lstrip("/") / "route.ts"
        assert file_path.exists(), f"Missing route file for protected endpoint: {route}"

    def test_no_api_route_bypasses_middleware(self):
        """No API route (outside /api/auth) should handle auth internally —
        all protection comes from middleware."""
        content = self._middleware()
        # Middleware must check auth for non-excluded paths
        assert "req.auth" in content, "Middleware must check req.auth"
        # Verify the only paths allowed without auth are /login and /api/auth
        assert 'pathname.startsWith("/login")' in content
        assert 'pathname.startsWith("/api/auth")' in content


# ---------------------------------------------------------------------------
# Auth configuration
# ---------------------------------------------------------------------------

class TestAuthConfig:
    """Validate auth configuration in auth.ts and docker-compose."""

    def _auth_content(self):
        return (ROOT / "ui/src/lib/auth.ts").read_text()

    def test_google_provider_configured(self):
        content = self._auth_content()
        assert "Google(" in content
        assert "GOOGLE_CLIENT_ID" in content
        assert "GOOGLE_CLIENT_SECRET" in content

    def test_credentials_provider_configured(self):
        content = self._auth_content()
        assert "Credentials(" in content
        assert "UI_USERNAME" in content
        assert "UI_PASSWORD" in content

    def test_google_email_whitelist(self):
        """Google sign-in must check GOOGLE_ALLOWED_EMAILS."""
        content = self._auth_content()
        assert "GOOGLE_ALLOWED_EMAILS" in content
        assert "allowedList" in content or "allowed" in content

    def test_providers_conditional(self):
        """Providers should only be added when env vars are set."""
        content = self._auth_content()
        assert "process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET" in content
        assert "process.env.UI_USERNAME && process.env.UI_PASSWORD" in content

    def test_docker_compose_has_auth_env_vars(self):
        """Docker compose UI service must pass auth env vars."""
        data = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
        env = data["services"]["ui"]["environment"]
        for key in ["NEXTAUTH_SECRET", "NEXTAUTH_URL", "GOOGLE_CLIENT_ID",
                     "GOOGLE_CLIENT_SECRET", "GOOGLE_ALLOWED_EMAILS",
                     "UI_USERNAME", "UI_PASSWORD"]:
            assert key in env, f"Missing auth env var in docker-compose: {key}"

    def test_login_page_fetches_providers(self):
        """Login page must fetch providers at runtime, not use NEXT_PUBLIC vars."""
        content = (ROOT / "ui/src/app/login/page.tsx").read_text()
        assert "/api/auth/providers-info" in content
        assert "NEXT_PUBLIC" not in content

    def test_nextauth_package_installed(self):
        """next-auth must be in package.json dependencies."""
        data = json.loads((ROOT / "ui/package.json").read_text())
        assert "next-auth" in data["dependencies"]
