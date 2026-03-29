# inotagent — Overview

## What is inotagent

inotagent is a Python middleware that replaces OpenClaw as the agent runtime in inotives_aibots. One async Python process per agent, handling: Discord bot, LLM API calls, tool execution, scheduling, and database persistence.

The agents are developer-focused. Their primary tool is **opencode** — an AI coding CLI that handles all code reading, writing, debugging, and refactoring. inotagent orchestrates the agent's reasoning loop and delegates coding work to opencode.

No Node.js. No black box gateway. Just Python.

## Core philosophy: Code-first, not LLM-first

Agents are developers. They solve problems by writing and running code — not by feeding data into the LLM.

**Wrong approach** (LLM-first):
```
"Analyze this CSV" → dump 50K rows into LLM context → burn 100K tokens → get a summary
```

**Right approach** (code-first):
```
"Analyze this CSV" → read first 20 rows to understand structure → write a Python script
→ run it via opencode → script outputs results → agent interprets the output
```

This applies to everything:
- **Data analysis** — write scripts, don't push data to LLM
- **Log investigation** — grep/awk first, feed only relevant lines to LLM
- **Code review** — use git diff, read specific files, don't load entire repos
- **Testing** — write and run tests, don't ask LLM to mentally execute code
- **Database queries** — write SQL, run it, interpret results

**Reuse before reinvent.** Before writing new code, the agent should:
1. Check if a similar script already exists in the workspace (`scripts/`, `tools/`)
2. Search memory for past solutions to similar requests (`memory_search`)
3. Check if existing CLI tools already solve the problem (`--help`)
4. Only write new code if nothing reusable exists

When the agent *does* write a useful script, it should save it to the workspace `scripts/` directory and store a memory: `memory_store("wrote scripts/analyze_logs.py for parsing nginx logs", tags=["script", "logs", "nginx"])`. Next time a similar request comes in, memory search finds it.

The LLM's job is to **reason about what to do** and **write code to do it**. The actual work happens in tools (opencode, shell, scripts). This keeps token usage low and results accurate — code doesn't hallucinate.

## Why replace OpenClaw

| Problem | Impact |
|---------|--------|
| **Exec approval hell** | Three-layer approval system (exec-approvals.json, openclaw.json, channel execApprovals) blocks agents from running commands via Discord. Hours debugging, still unreliable. |
| **Black box** | Node.js gateway we can't debug or extend. Cron silently fails. Exec denials have no useful logs. |
| **Heavy image** | OpenClaw base image is 2GB+. Our needs fit in ~200MB (python:3.12-slim). |
| **Limited Discord** | No embeds, slash commands, buttons, or fine-grained thread control. |
| **Fragile cron** | Requires gateway health before cron setup. Cron CLI can silently fail. |
| **Config complexity** | YAML→JSON transform across 4 files to produce openclaw.json. |
| **Dependency risk** | Pinned to external Docker image. Breaking changes or abandonment locks us. |

## What we gain

- **Full exec control** — our container, our rules. No approval layers.
- **Channel abstraction** — Discord now, Slack/WhatsApp/Telegram later. Each is just a connector implementing the same interface.
- **opencode as primary tool** — agents delegate all coding to opencode CLI, with full control over how it's invoked.
- **Simpler debugging** — it's our Python code, fully observable.
- **Smaller images** — python:3.12-slim (~200MB vs 2GB+).
- **Custom tools** — define any tool the LLM can call.
- **No boot sequence hacks** — no waiting for gateway health.

### Security & deployment advantages

- **Container-scoped access** — each agent runs in its own isolated container. No access to the host filesystem, no shared runtimes, no cross-agent contamination. An agent can only touch what's inside its container + its Postgres schema.
- **No host pollution** — OpenClaw installs globally on the host (Node.js, npm packages, config in `~/.openclaw/`). Reinstalling or upgrading risks registry pollution, stale configs, and version conflicts. inotagent is fully containerized — `docker rm` and it's gone, `docker run` and it's back. Clean every time.
- **Easy redeploy** — rebuild image, restart container. No residual state on the host. No orphaned processes, no lingering config files.
- **Credentials isolation** — each agent's `.env` is mounted only into its own container. No shared credential store. Compromised agent can't access another agent's tokens.
- **Reproducible environments** — everything is in the Dockerfile. No "works on my machine" — same image runs the same everywhere.

## Architecture

```
┌──────────────────────────────────────────┐
│  Agent Container (1 per agent)           │
│                                          │
│  ┌────────────────────┐  ┌───────────┐  │
│  │  Channel Layer     │  │ Scheduler │  │
│  │                    │  │ (asyncio) │  │
│  │  ┌──────────────┐  │  └─────┬─────┘  │
│  │  │ Discord      │  │        │         │
│  │  │ (discord.py) │  │        │         │
│  │  ├──────────────┤  │        │         │
│  │  │ Slack        │  │        │         │
│  │  │ (future)     │  │        │         │
│  │  ├──────────────┤  │        │         │
│  │  │ WhatsApp     │  │        │         │
│  │  │ (future)     │  │        │         │
│  │  └──────┬───────┘  │        │         │
│  └─────────┼──────────┘        │         │
│            ▼                   ▼         │
│  ┌──────────────────────────────────┐    │
│  │          Agent Loop              │    │
│  │                                  │    │
│  │  1. Build prompt                 │    │
│  │     (AGENTS.md + history         │    │
│  │      + tool defs)                │    │
│  │  2. Call LLM API                 │    │
│  │  3. Parse response            ◀──┐   │
│  │  4. Tool call? ─── yes ──────────┘   │
│  │         │ no                          │
│  │  5. Send response                    │
│  └──────────────┬───────────────────┘    │
│                 │                         │
│  ┌──────────────▼───────────────────┐    │
│  │           Tool Layer             │    │
│  │                                  │    │
│  │  opencode  — coding (PRIMARY)    │    │
│  │  shell     — subprocess.run      │    │
│  │  files     — read/write/glob     │    │
│  │  browser   — Playwright          │    │
│  │  platform  — tasks/messages      │    │
│  │  github    — gh CLI              │    │
│  └──────────────┬───────────────────┘    │
│                 │                         │
│  ┌──────────────▼───────────────────┐    │
│  │          Postgres                │    │
│  │  conversations, tasks,           │    │
│  │  messages, config, memory        │    │
│  └──────────────────────────────────┘    │
└──────────────────────────────────────────┘
```

### Core loop (pseudocode)

```python
async def agent_loop(message: str, conversation_id: str):
    system = load_system_prompt()       # AGENTS.md + TOOLS.md
    history = load_history(conversation_id)
    tools = get_tool_definitions()

    response = await llm.chat(
        system=system,
        messages=history + [user_msg(message)],
        tools=tools,
    )

    while response.has_tool_calls():
        results = await execute_tools(response.tool_calls)
        response = await llm.chat(
            messages=[...history, user_msg, assistant_msg, tool_results],
            tools=tools,
        )

    save_history(conversation_id, message, response)
    return response.text
```

## opencode — Primary Coding Tool

Agents are developer-focused. All coding work is delegated to [opencode CLI](https://opencode.ai/docs/cli/).

**Default mode: `opencode run`** — non-interactive, one-shot per task. Simple, no process management.

| Mode | Command | Use case |
|------|---------|----------|
| **Non-interactive** | `opencode run "prompt"` | One-shot coding tasks (create file, fix bug, refactor) |
| **Session continue** | `opencode run --session ID "prompt"` | Multi-step work within same context |
| **Headless server** | `opencode serve --port 4096` | Future: persistent backend if cold boot becomes a bottleneck |
| **Attach to server** | `opencode run --attach http://localhost:4096 "prompt"` | Future: connect to persistent server |

Start with `opencode run`. If cold boot time becomes a problem, switch to `opencode serve` + `run --attach` — it's a one-line change in the tool executor.

The agent's LLM reasons about *what* to do, then calls the `opencode` tool to do the actual coding. The agent handles git, task management, communication — opencode handles code.

## What we keep from inotives_aibots

| Component | Status |
|-----------|--------|
| DB schema (agents, spaces, messages, tasks, config, agent_status, agent_repos) | Reuse as-is |
| Config files (agent.yml, AGENTS.md, TOOLS.md, models.yml, platform.yml) | Reuse, TOOLS.md slimmed down. MEMORY.md dropped — replaced by pgvector memory_search tool |
| Platform tools (tasks.py, messaging.py) | Port to async, import directly |
| Boot sequence concept (DB migrate → register → sync repos → start) | Adapt for Python entrypoint |
| Docker Compose pattern (1 container per agent) | Reuse, different base image |
| Postgres migrations (dbmate) | Reuse as-is |

## What we remove (after migration)

- `core/Dockerfile.base` (OpenClaw base image)
- `core/runtime/generate_openclaw_config.py` (openclaw.json generation)
- `core/runtime/config_sync.py` (hot-reload to openclaw.json)
- `core/runtime/setup_crons.py` (OpenClaw cron CLI)
- `exec-approvals.json` and all exec approval logic
- All `openclaw` CLI invocations

## Tech stack

- **Language**: Python 3.12
- **Package manager**: uv (pyproject.toml + uv.lock)
- **Channels**: discord.py (Discord), future: slack-sdk (Slack), others
- **LLM clients**: anthropic SDK (Anthropic), httpx (OpenAI-compatible: NVIDIA, Groq, Ollama, OpenAI)
- **Database**: psycopg 3 (async) + existing Postgres + pgvector
- **Scheduling**: asyncio tasks
- **Coding tool**: opencode CLI (`opencode run`)
- **Browser**: Playwright (async)
- **Base image**: python:3.12-slim
- **Containers**: Docker + docker-compose

## Project structure

```
inotagent/
├── src/
│   └── inotagent/
│       ├── __init__.py
│       ├── main.py              # Entry point — start channels + scheduler + agent loop
│       ├── loop.py              # Agent loop (prompt → LLM → tools → respond)
│       ├── channels/
│       │   ├── __init__.py
│       │   ├── base.py          # Channel protocol (abstract interface)
│       │   ├── discord.py       # Discord connector (discord.py)
│       │   ├── slack.py         # Slack connector (future)
│       │   └── whatsapp.py      # WhatsApp connector (future)
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── client.py        # Unified LLM client interface
│       │   ├── anthropic.py     # Anthropic provider (SDK)
│       │   ├── openai_compat.py # OpenAI-compatible provider (httpx)
│       │   └── tokens.py        # Token counting, context truncation
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── registry.py      # Tool definition registry
│       │   ├── executor.py      # Tool call dispatcher
│       │   ├── opencode.py      # opencode CLI integration (PRIMARY)
│       │   ├── shell.py         # Shell command execution
│       │   ├── files.py         # File read/write/search
│       │   ├── browser.py       # Web browsing (Playwright)
│       │   └── platform.py      # Tasks, messages, repos (port from runtime/)
│       ├── config/
│       │   ├── __init__.py
│       │   ├── agent.py         # Load agent.yml, AGENTS.md, TOOLS.md
│       │   ├── models.py        # Model registry (models.yml)
│       │   └── platform.py      # Platform config from DB
│       ├── db/
│       │   ├── __init__.py
│       │   ├── pool.py          # Async connection pool
│       │   ├── conversations.py # Conversation history
│       │   └── memory.py        # Vector memory (pgvector)
│       └── scheduler/
│           ├── __init__.py
│           └── cron.py          # Scheduled tasks
├── tests/
├── pyproject.toml
├── Dockerfile
└── docker-compose.yml
```

## Implementation phases

| Phase | Name | Goal | Complexity |
|-------|------|------|------------|
| 1 | [Foundation](01_foundation.md) | Agent loop works: config → prompt → LLM → response (CLI test) | Medium |
| 2 | [Tool System](02_tools.md) | Agent uses tools: opencode, shell, files, platform tools | Large |
| 3 | [Channels](03_channels.md) | Channel abstraction + Discord connector. Slack, WhatsApp, etc. later. | Medium |
| 4 | [Persistence](04_persistence.md) | Conversation history, context management, memory | Medium |
| 5 | [Scheduler](05_scheduler.md) | Heartbeat (60s, detects new work) + cron (30min, deep task sessions) | Medium |
| 6 | [Integration](06_integration.md) | Docker, migration from OpenClaw, agent-to-agent messaging | Large |

## Decisions made

1. **opencode run** — Start with `opencode run` (non-interactive, one-shot). Switch to `opencode serve` + `run --attach` later if cold boot becomes a bottleneck.
2. **Channel abstraction** — Discord is just one connector. Build a generic `Channel` protocol so adding Slack, WhatsApp, Telegram is just implementing a new class.

## Decisions made

3. **Concurrency** — Default: 1 conversation at a time per agent (sequential queue). Configurable via `agent.yml` `parallel: true` for agents using paid-tier LLM tokens that can handle concurrent requests.
4. **Streaming** — Wait for full LLM response before sending. Simpler, works cleanly with tool call loop, consistent across all channels. Streaming can be added later if needed.
5. **Browser tool** — Yes, use Playwright. Added as a tool in Phase 2.
6. **Token efficiency** — TOOLS.md is behavioral guidance only ("use opencode for coding, never write code directly"). Detailed tool usage is already in the LLM tool definitions (function calling schema) which are required by the API. No duplication. Tool results truncated before storing in history.
7. **Memory** — MEMORY.md dropped. Memory stored in Postgres, searched via tag-based + full-text search. No embedding model dependency. pgvector embeddings can be added later if needed.
8. **Channel config in DB** — Channel settings (enabled, allowFrom, guilds, etc.) stored in `platform.config`, not YAML. Change at runtime via SQL — no redeploy. YAML only holds `token_env` (which env var has the secret).
