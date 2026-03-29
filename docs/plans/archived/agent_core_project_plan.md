# Agent Core — Project Plan

## Overview

A lightweight Python middleware that replaces OpenClaw as the agent runtime for the inotives_aibots platform. It handles the full loop: receive messages (Discord), build prompts, call LLM APIs, execute tools, and respond — all in a single Python process per agent.

## Why Replace OpenClaw

### Problems with OpenClaw

1. **Exec approval hell** — Three-layer approval system (exec-approvals.json, openclaw.json tools.exec.security, channel-level execApprovals) that blocks agents from running commands, especially when instructions come from Discord. Spent significant time debugging and still unreliable.
2. **Black box** — OpenClaw is a Node.js gateway we can't easily debug or extend. When something breaks (cron not firing, exec denied, gateway crash), we're guessing at internals.
3. **Heavy base image** — OpenClaw Docker image is 2GB+. Our actual runtime needs are much simpler.
4. **Limited control over Discord** — OpenClaw's Discord integration doesn't give us fine-grained control over reactions, embeds, threads, slash commands, or buttons.
5. **Cron fragility** — OpenClaw cron requires the gateway to be healthy first, adding complexity to boot sequence. Cron jobs created via CLI can silently fail.
6. **Config generation complexity** — We generate `openclaw.json` from platform.yml + models.yml + agent.yml + env vars. With our own runtime, config is just Python dicts.
7. **Dependency risk** — Pinned to `ghcr.io/openclaw/openclaw:2026.3.12`. Any breaking change or abandoned project leaves us stuck.

### What We Gain

- **Full exec control** — Our container, our rules. No approval layers.
- **Direct Discord bot** — discord.py gives us full API access (reactions, embeds, slash commands, threads, buttons).
- **Simpler debugging** — It's our Python code, fully observable.
- **Smaller images** — python:3.12-slim base (~150MB vs 2GB+).
- **Custom tool definitions** — Define any tool the LLM can call, not limited to OpenClaw's built-in set.
- **Custom message routing** — Full control over agent-to-agent communication.
- **No boot sequence hacks** — No waiting for gateway health before setting up crons or approvals.

## What OpenClaw Actually Does (and what we replace)

| OpenClaw Feature | What It Does | Our Replacement |
|---|---|---|
| Gateway | HTTP server routing messages to LLM | Direct LLM API calls (httpx) |
| Discord channel | Discord bot integration | discord.py bot |
| LLM routing | Multi-provider API calls with fallbacks | Simple HTTP client with provider config |
| Tool execution | Shell exec, file I/O, browser | subprocess.run(), pathlib, (browser later) |
| Session management | Conversation history, context window | Postgres-backed message history + token counting |
| Cron system | Scheduled prompts to agents | asyncio tasks / APScheduler |
| Workspace files | AGENTS.md, TOOLS.md, MEMORY.md as system context | Read files, prepend to prompt |
| Memory search | Vector-based memory retrieval | Postgres + pgvector (already have this) |
| Exec approvals | Multi-layer command allowlisting | Not needed — our container, our rules |
| Config | openclaw.json | Python config from YAML + env |

## Architecture

```
┌─────────────────────────────────┐
│  Agent Container (1 per agent)  │
│                                 │
│  ┌───────────┐                  │
│  │ Discord   │──┐               │
│  │ Bot       │  │               │
│  └───────────┘  │               │
│                 ▼               │
│  ┌──────────────────┐          │
│  │  Agent Loop       │          │
│  │                   │          │
│  │  receive message  │          │
│  │       ▼           │          │
│  │  build prompt     │          │
│  │  (system + hist   │          │
│  │   + tools)        │          │
│  │       ▼           │          │
│  │  call LLM API  ◀──┐         │
│  │       ▼           │         │
│  │  parse response   │         │
│  │       ▼           │         │
│  │  tool call? ──yes─┘         │
│  │       │no                    │
│  │       ▼                      │
│  │  send response    │          │
│  └────────┬─────────┘          │
│           │                     │
│  ┌────────▼─────────┐          │
│  │  Scheduler        │          │
│  │  (cron tasks)     │          │
│  └──────────────────┘          │
│                                 │
│  ┌──────────────────┐          │
│  │  Postgres         │          │
│  │  - messages       │          │
│  │  - tasks          │          │
│  │  - memory/vectors │          │
│  │  - config         │          │
│  │  - agent_status   │          │
│  └──────────────────┘          │
└─────────────────────────────────┘
```

### Core Loop (pseudocode)

```python
async def agent_loop(message: str, conversation_id: str):
    # 1. Load context
    system_prompt = load_system_prompt()  # AGENTS.md + TOOLS.md
    history = load_conversation_history(conversation_id)
    tools = get_tool_definitions()

    # 2. Call LLM
    response = await llm_client.chat(
        model=agent_config.model,
        system=system_prompt,
        messages=history + [{"role": "user", "content": message}],
        tools=tools,
    )

    # 3. Tool use loop
    while response.has_tool_calls():
        results = await execute_tools(response.tool_calls)
        response = await llm_client.chat(
            messages=history + [..., tool_results],
            tools=tools,
        )

    # 4. Save and return
    save_to_history(conversation_id, message, response)
    return response.text
```

## Tech Stack

- **Language**: Python 3.12
- **Package manager**: uv (pyproject.toml + uv.lock)
- **Discord**: discord.py
- **HTTP client**: httpx (async, for LLM API calls)
- **Database**: psycopg (async) + existing Postgres + pgvector
- **Scheduling**: asyncio tasks (simple) or APScheduler (if we need cron expressions)
- **Token counting**: tiktoken (OpenAI models) / anthropic tokenizer
- **Base image**: python:3.12-slim
- **Container**: Docker + docker-compose

## Project Structure

```
agent_core/
├── src/
│   └── agent_core/
│       ├── __init__.py
│       ├── main.py            # Entry point — start bot + scheduler
│       ├── bot.py             # Discord bot (message listener, response sender)
│       ├── loop.py            # Agent loop (prompt assembly → LLM → tools → respond)
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── client.py      # Multi-provider LLM client
│       │   ├── providers.py   # Provider configs (Anthropic, OpenAI, NVIDIA, Google, Ollama)
│       │   └── tokens.py      # Token counting and context window management
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── registry.py    # Tool definition registry
│       │   ├── executor.py    # Tool call dispatcher
│       │   ├── shell.py       # Shell command execution (subprocess)
│       │   ├── files.py       # File read/write/search
│       │   ├── platform.py    # Platform tools (tasks, messages, repos)
│       │   └── coding.py      # opencode / claude-code delegation
│       ├── config/
│       │   ├── __init__.py
│       │   ├── agent.py       # Load agent config (agent.yml, AGENTS.md, TOOLS.md)
│       │   ├── models.py      # Model registry (models.yml)
│       │   └── platform.py    # Platform config (from DB)
│       ├── db/
│       │   ├── __init__.py
│       │   ├── connection.py  # Async Postgres connection pool
│       │   ├── messages.py    # Conversation history storage/retrieval
│       │   ├── memory.py      # Vector memory (pgvector)
│       │   └── migrations.py  # Schema setup
│       └── scheduler/
│           ├── __init__.py
│           └── cron.py        # Scheduled tasks (task checks, health reports)
├── tests/
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Implementation Phases

### Phase 1: Core Loop + LLM Client
**Goal**: Agent can receive a prompt, call an LLM, and return a response.

- [ ] Project scaffold (pyproject.toml, uv, src layout)
- [ ] LLM client with multi-provider support (Anthropic, OpenAI-compatible for NVIDIA/Groq/Ollama)
- [ ] Model registry loader (reuse models.yml format)
- [ ] Prompt assembly (system prompt from AGENTS.md + TOOLS.md + conversation history)
- [ ] Basic agent loop (prompt → LLM → response, no tools yet)
- [ ] Token counting and context window truncation
- [ ] Test with CLI input (no Discord yet)

### Phase 2: Tool Execution
**Goal**: Agent can use tools (shell, files, platform_tools) in response to prompts.

- [ ] Tool definition format (compatible with Anthropic/OpenAI function calling)
- [ ] Tool registry (register available tools per agent)
- [ ] Shell executor (subprocess.run with timeout, working directory)
- [ ] File tools (read, write, search, list)
- [ ] Platform tools (task CRUD, message send, repo list)
- [ ] Coding tool (delegate to opencode CLI)
- [ ] Tool call loop (LLM → tool call → execute → feed result back → repeat)

### Phase 3: Discord Bot
**Goal**: Agent responds to Discord messages and DMs.

- [ ] discord.py bot setup (token from env, intents)
- [ ] Message listener (mentions, DMs, configured channels)
- [ ] Response sender (chunked for long messages, markdown formatting)
- [ ] Conversation threading (map Discord threads to conversation IDs)
- [ ] Typing indicator while LLM is thinking
- [ ] Error handling (graceful failure messages)

### Phase 4: Database Integration
**Goal**: Persistent conversation history, config from DB, health reporting.

- [ ] Async Postgres connection pool
- [ ] Conversation history storage and retrieval
- [ ] Config sync from platform.config table
- [ ] Agent status reporting (health checks)
- [ ] Reuse existing platform schema (agents, messages, tasks, config, agent_status)

### Phase 5: Scheduler + Cron
**Goal**: Agent autonomously checks tasks on a schedule.

- [ ] Async scheduler (asyncio-based or APScheduler)
- [ ] Task check cron (configurable interval from DB)
- [ ] Role-based prompts (worker vs manager)
- [ ] Health check reporting on schedule

### Phase 6: Agent-to-Agent Communication
**Goal**: Agents can message each other directly.

- [ ] Platform messaging (spaces + messages table)
- [ ] Message polling or notification (check for new messages periodically)
- [ ] Direct send to another agent (insert into messages table)
- [ ] #tasks space notifications on task status changes

### Phase 7: Integration + Migration
**Goal**: Replace OpenClaw in inotives_aibots.

- [ ] Dockerfile (python:3.12-slim based)
- [ ] docker-compose integration with existing inotives_aibots setup
- [ ] Entrypoint script (DB migration, config load, start bot)
- [ ] Migrate one agent (robin) as test
- [ ] Validate: Discord works, tasks work, crons work, agent-to-agent works
- [ ] Migrate remaining agents
- [ ] Remove OpenClaw dependency from inotives_aibots

## LLM Provider Support

Reuse the existing `models.yml` format:

```yaml
models:
  - id: nvidia-glm5
    provider: nvidia
    model: nvidia/glm-4-9b-chat
    api_key_env: NVIDIA_API_KEY
    base_url: https://integrate.api.nvidia.com/v1
    context_window: 131072
    max_tokens: 16384

  - id: claude-sonnet
    provider: anthropic
    model: claude-sonnet-4-20250514
    api_key_env: ANTHROPIC_API_KEY
    context_window: 200000
    max_tokens: 8192
```

Provider mapping:
- **Anthropic** → `anthropic` Python SDK (Messages API)
- **OpenAI / NVIDIA / Groq / Ollama** → `httpx` to OpenAI-compatible `/v1/chat/completions`
- **Google** → `httpx` to Gemini API

All providers support the same interface: `chat(model, system, messages, tools) → response`

## Tool Definition Format

Use Anthropic's tool format as the canonical schema (convert to OpenAI format for compatible providers):

```python
{
    "name": "shell",
    "description": "Execute a shell command and return stdout/stderr",
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The command to run"},
            "working_dir": {"type": "string", "description": "Working directory"},
            "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 120},
        },
        "required": ["command"],
    },
}
```

## What We Keep from inotives_aibots

- **DB schema** — platform.agents, spaces, messages, tasks, config, agent_status, agent_repos
- **Config files** — agent.yml, AGENTS.md, TOOLS.md, MEMORY.md, models.yml, platform.yml
- **platform_tools** — Task CRUD, messaging (import as Python module, not CLI)
- **Boot sequence concept** — DB migration → register agent → sync repos → start
- **Docker Compose** — Same pattern, just different base image

## What We Remove from inotives_aibots (after migration)

- `core/Dockerfile.base` (no more OpenClaw base image)
- `core/runtime/generate_openclaw_config.py` (no more openclaw.json)
- `core/runtime/config_sync.py` (config read directly from DB)
- `core/runtime/setup_crons.py` (scheduler is built-in)
- OpenClaw-specific entrypoint steps (exec-approvals.json, openclaw gateway)
- All `openclaw` CLI calls

## Open Questions

1. **Browser tool** — OpenClaw has a built-in browser. Do we need it? If yes, use Playwright.
2. **Streaming** — Stream LLM responses to Discord (typing → partial messages) or wait for full response?
3. **Concurrency** — One conversation at a time per agent, or allow parallel? (Current: maxConcurrent=1)
4. **Memory/RAG** — Use pgvector for semantic memory search, or keep it simple with keyword search for now?
5. **Repo name** — `agent_core`? `inotives_agent_core`? `claw`?
