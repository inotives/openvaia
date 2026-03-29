# Phase 6: Docker & Migration

**Goal**: Package inotagent as a Docker image and replace OpenClaw in the inotives_aibots deployment, one agent at a time.

**Delivers**: Agent containers running inotagent instead of OpenClaw, with the same external behavior (Discord, tasks, messaging) but better reliability and control.

**Complexity**: Large

## Dependencies

- All previous phases (1–5)

## What to build

### 6.1 Dockerfile

Replace the OpenClaw-based `core/Dockerfile.base` with a Python-only image:

```dockerfile
FROM python:3.12-slim AS base

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl libpq-dev build-essential ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update && apt-get install -y gh && rm -rf /var/lib/apt/lists/*

# opencode CLI (primary coding tool)
RUN curl -fsSL https://opencode.ai/install.sh | sh
ENV PATH="/root/.opencode/bin:$PATH"

# uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Python deps
WORKDIR /app
COPY inotagent/pyproject.toml inotagent/uv.lock ./inotagent/
RUN cd inotagent && uv sync --no-dev --frozen

# Copy runtime code
COPY inotagent/src/ ./inotagent/src/
COPY core/runtime/db.py core/runtime/config.py core/runtime/tasks.py core/runtime/messaging.py ./core/runtime/
COPY core/models.yml core/platform.yml ./core/
COPY infra/ ./infra/

# Workspace directory
RUN mkdir -p /workspace/repos

ENV WORKSPACE_DIR=/workspace
ENV PYTHONPATH=/app

CMD ["bash", "/app/inotagent/entrypoint.sh"]
```

**Image size comparison:**
- OpenClaw base: ~2GB+
- python:3.12-slim + deps: ~200-300MB

### 6.2 Entrypoint script

Port the boot sequence from `core/runtime/entrypoint.sh`, simplified:

```bash
#!/usr/bin/env bash
set -euo pipefail

AGENT_NAME="${AGENT_NAME:?AGENT_NAME required}"
echo "=== inotagent boot: ${AGENT_NAME} ==="

# Step 1: Git credentials
if [[ -n "${GITHUB_TOKEN_PATS:-}" ]]; then
    git config --global url."https://${GITHUB_TOKEN_PATS}@github.com/".insteadOf "https://github.com/"
fi
if [[ -n "${GIT_EMAIL:-}" ]]; then
    git config --global user.email "${GIT_EMAIL}"
    git config --global user.name "${AGENT_NAME}"
fi

# Step 2: Ensure database exists
python -c "
import psycopg2
conn = psycopg2.connect(host='${POSTGRES_HOST}', port=${POSTGRES_PORT:-5432}, user='${POSTGRES_USER}', password='${POSTGRES_PASSWORD}', dbname='postgres')
conn.autocommit = True
cur = conn.cursor()
cur.execute(\"SELECT 1 FROM pg_database WHERE datname = '${POSTGRES_DB}'\")
if not cur.fetchone():
    cur.execute('CREATE DATABASE ${POSTGRES_DB}')
    print('Created database ${POSTGRES_DB}')
conn.close()
"

# Step 3: Run migrations
SCHEMA="${PLATFORM_SCHEMA:-platform}"
dbmate --url "postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT:-5432}/${POSTGRES_DB}?sslmode=disable" \
    --migrations-dir /app/infra/postgres/migrations \
    --schema-file /dev/null \
    --no-dump-schema \
    migrate 2>&1 | sed "s/platform\./${SCHEMA}./g"

# Step 4: Register agent + sync repos
cd /app
python -m inotagent.bootstrap

# Step 5: Start inotagent
exec uv run --directory /app/inotagent python -m inotagent \
    --agent-name "${AGENT_NAME}" \
    --agent-dir "/app/agents/${AGENT_NAME}" \
    --workspace-dir "${WORKSPACE_DIR:-/workspace}"
```

### 6.3 Bootstrap script (`inotagent/bootstrap.py`)

Port from `core/runtime/main.py`:

```python
"""One-time bootstrap: register agent, sync repos, announce."""

async def bootstrap(agent_name: str):
    # Register agent
    await register_agent(agent_name)

    # Ensure #tasks and #public spaces
    await ensure_space("tasks", "room")
    await ensure_space("public", "public")

    # Add agent to spaces
    await add_to_space(agent_name, "tasks")
    await add_to_space(agent_name, "public")

    # Announce boot
    await send_message(agent_name, "public", f"🟢 {agent_name} is online (inotagent)")

    # Announce pending tasks
    await announce_pending_tasks(agent_name)

    # Sync repos
    await sync_repos(agent_name)
```

### 6.4 Agent-to-agent messaging

Port from `core/runtime/messaging.py`, upgrade to async:

```python
async def send_message(from_agent: str, space_name: str, body: str, metadata: dict | None = None):
    """Send a message to a named space."""
    space_id = await get_space_id(space_name)
    async with get_connection() as conn:
        await conn.execute(
            f"""INSERT INTO {SCHEMA}.messages (space_id, from_agent, body, metadata, created_at)
                VALUES (%s, %s, %s, %s, NOW())""",
            (space_id, from_agent, body, json.dumps(metadata or {})),
        )

async def poll_messages(agent_name: str, interval: int = 30):
    """Check for new messages directed to this agent (in DM or room spaces)."""
    # Run as a scheduler task
    # Check messages table for unread messages in agent's spaces
    # Feed new messages into the agent loop
```

### 6.5 docker-compose changes

Update service definitions to use inotagent:

```yaml
services:
  robin:
    build:
      context: .
      dockerfile: inotagent/Dockerfile
      args:
        AGENT_NAME: robin
    container_name: agent_robin
    env_file:
      - .env
      - agents/robin/.env
    environment:
      AGENT_NAME: robin
      PLATFORM_SCHEMA: openvaia
    volumes:
      - robin_workspace:/workspace
    deploy:
      resources:
        limits:
          memory: 2g      # Much less than 4g needed for Node.js
          cpus: "1.0"
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - platform

  # Same pattern for ino
```

### 6.6 Agent Dockerfile (per-agent)

Each agent copies its workspace files:

```dockerfile
FROM inotagent-base AS agent

ARG AGENT_NAME
COPY agents/${AGENT_NAME}/agent.yml /app/agents/${AGENT_NAME}/agent.yml
COPY agents/${AGENT_NAME}/AGENTS.md /workspace/AGENTS.md
COPY agents/${AGENT_NAME}/TOOLS.md /workspace/TOOLS.md
# MEMORY.md not copied — memory is in pgvector, accessed via memory_search tool
```

## Migration strategy

### Step 1: Build & test locally
- Build inotagent image
- Run one agent (robin) with inotagent
- Verify: Discord responds, tasks work, opencode runs, cron fires

### Step 2: Run alongside OpenClaw
- Robin runs on inotagent, Ino stays on OpenClaw
- Verify inter-agent messaging works (both write to same DB tables)
- Monitor for a day

### Step 3: Migrate remaining agents
- Switch Ino to inotagent
- Verify manager workflows (task creation, delegation, review)

### Step 4: Remove OpenClaw
- Delete `core/Dockerfile.base` (OpenClaw-based)
- Delete `core/runtime/generate_openclaw_config.py`
- Delete `core/runtime/config_sync.py`
- Delete `core/runtime/setup_crons.py`
- Delete `core/runtime/healthcheck.py` (replaced by scheduler health)
- Update Makefile targets
- Update CLAUDE.md

### Rollback plan
- Keep OpenClaw Dockerfiles until migration is confirmed stable
- docker-compose can switch back by changing the build context
- DB schema is unchanged — both runtimes use the same tables

## Files to create/modify

| File | Action |
|------|--------|
| `inotagent/Dockerfile` | Create — base image |
| `inotagent/entrypoint.sh` | Create — boot sequence |
| `src/inotagent/bootstrap.py` | Create — one-time setup |
| `docker-compose.yml` | Modify — update service definitions |
| `agents/*/Dockerfile` | Modify — extend inotagent-base |
| `Makefile` | Modify — update build targets |
| `CLAUDE.md` | Modify — update docs |

## Existing code to port

- `core/runtime/entrypoint.sh` → `inotagent/entrypoint.sh` (simplified, no OpenClaw)
- `core/runtime/main.py` → `inotagent/bootstrap.py` (register, announce, sync repos)
- `core/runtime/messaging.py` → `inotagent/db/` or `tools/platform.py` (async version)

## How to verify

1. `make deploy AGENT=robin` → robin comes online with inotagent (check Docker logs)
2. DM robin on Discord → responds correctly
3. `make task-list AGENT=robin` → tasks visible
4. Robin picks up a task on cron → calls opencode → makes progress
5. Robin sends message to #tasks space → Ino (still on OpenClaw) sees it
6. Image size: `docker images | grep inotagent` → should be ~200-300MB
7. Memory usage: `docker stats agent_robin` → should be well under 2g limit
