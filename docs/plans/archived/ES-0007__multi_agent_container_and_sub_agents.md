# ES-0007 — Multi-Agent Container & Sub-Agents

## Status: PENDING

## Core Concept

**Container = Company. Agent = Worker.**

A container is like a company office — it provides the infrastructure (DB pool, browser, embedding client, Python runtime). Agents are workers who walk into that office and start working.

You can put all workers in one company (single container), or split them across multiple companies (multiple containers). The workers don't care — they just need a desk and a brain.

```
Deployment A — Small machine, all-in-one:
┌─────────────────────────────┐
│  openvaia (1 container)     │
│  ino, robin, alex           │
└─────────────────────────────┘

Deployment B — Separate teams:
┌──────────────────┐  ┌──────────────────┐
│ research-team    │  │ trading-team     │
│ ino, kai         │  │ robin, alex      │
└──────────────────┘  └──────────────────┘

Deployment C — Current (1:1, still works):
┌──────────┐  ┌──────────┐  ┌──────────┐
│ ino      │  │ robin    │  │ alex     │
└──────────┘  └──────────┘  └──────────┘
```

All three deployments use the same agent code, same image, same agent.yml. The only difference is the `AGENTS` env var. This is a deployment decision, not a code decision.

All 100 agent folders are baked into the image, but only agents listed in `AGENTS=ino,robin` are started. The rest sit dormant — zero resource cost.

---

## Problem

Current architecture: 1 agent = 1 Docker container. Each container runs its own Python process, DB connection pool, Playwright browser, embedding client, and heartbeat. With 2 agents, that's:

- 2 Python runtimes (~64 MiB each)
- 2 DB connection pools (2-10 connections each)
- 2 Playwright browser instances (lazy-loaded but heavy when active)
- 2 embedding client instances (same API, duplicated)
- 2 heartbeat loops doing similar DB queries

As we add more agents, this multiplies. On a small machine (e.g., LAN server with 8 GB RAM), running 5+ agents becomes expensive — not because of LLM calls, but because of duplicated infrastructure.

---

## Proposed Solution

Run multiple agents in a **single container / single Python process**. Each agent maintains its own identity (system prompt, skills, Discord bot, conversation context) but shares infrastructure (DB pool, browser, embedding client).

```
┌─────────────────────────────────────────────────┐
│               openvaia_agents                    │
│  Single Python process                           │
│  Shared: DB pool, Browser, Embedding client      │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │   ino    │  │  robin   │  │   alex   │      │
│  │ AgentLoop│  │ AgentLoop│  │ AgentLoop│      │
│  │ Heartbeat│  │ Heartbeat│  │ Heartbeat│      │
│  │ Discord  │  │ Discord  │  │ Discord  │      │
│  │ Skills   │  │ Skills   │  │ Skills   │      │
│  │ Model cfg│  │ Model cfg│  │ Model cfg│      │
│  └──────────┘  └──────────┘  └──────────┘      │
└─────────────────────────────────────────────────┘
```

Each agent still has its own model selection, fallback chain, skills, and channels — all configurable independently via agent.yml and DB overrides.

---

## Design Decisions (Resolved)

### 1. Env vars → Load from agent `.env` file at runtime

Each agent's `.env` file (`agents/{name}/.env`) is loaded into a per-agent dict at startup — not into OS-level env vars. This avoids collisions (two `DISCORD_BOT_TOKEN` values) and requires zero changes to the `.env` file format. Existing single-agent mode falls back to OS env vars.

### 2. CLI mode → Keep both single and multi-agent

- `--agent-dir /app/agents/robin` → single agent (current behavior, backward compatible)
- `--agents ino,robin` → multi-agent mode (new)

Single-agent mode stays for local development/testing.

### 3. Docker → Same image, `AGENTS` env var controls activation

One image bakes in all agent directories. `AGENTS=ino,robin` controls which agents start. Same image supports all deployment patterns (all-in-one, team split, 1:1).

```yaml
# All-in-one
agents:
  environment:
    AGENTS: ino,robin,alex

# Split by team
research-team:
  environment:
    AGENTS: ino,kai

# 1:1 (current)
ino:
  environment:
    AGENTS: ino
```

### 4. Browser → One shared Playwright, multiple pages

One Playwright browser instance shared across agents. Each browsing action gets its own page (already works this way). Browser singleton instead of per-agent instances.

### 5. Git → Per-agent workspace subdirectories

`/workspace/{agent_name}/repos/` — each agent's tools scoped to their subdirectory. No locking needed, zero conflict.

### 6. Scaling → Stateless containers, shared Postgres

Multiple containers can point to the same Postgres on different machines. Works with Docker Swarm, Kubernetes, or manual multi-machine. Only constraint: each channel bot token active in one container at a time.

### 7. Sub-agent tools → LLM-only for v1

Sub-agents (the `delegate` tool) get no tools initially — just a focused LLM call with a skill as system prompt. Tool access is a future enhancement.

### 8. Sub-agent model → Parent's model with optional override

Default: sub-agent uses parent's model + fallback chain. Optional `model` parameter for specifying a faster/cheaper model.

```python
delegate(skill="code_review", task="...")                          # parent model
delegate(skill="proofreading", task="...", model="groq-llama-3.3-70b")  # fast model
```

### 9. Agent models → Independent per agent

Each agent keeps its own `model_id` and `fallbacks` from `agent.yml` + DB overrides. Different agents in the same container can use different LLM models. Changeable via Admin UI without restart.

---

## What Changes

### `main.py` — Multi-agent entry point (~100-150 lines)

```python
async def async_main(args):
    # Shared infrastructure (once)
    await init_pool()
    init_embedding_client(platform.embedding)

    # Load agents from AGENTS env var or --agents CLI arg
    agent_names = parse_agents(args)

    # Per-agent setup
    runners = []
    for name in agent_names:
        agent_dir = agents_root / name
        agent_env = load_agent_env(agent_dir / ".env")  # per-agent env dict
        config = load_agent_config(agent_dir, models, platform)
        tool_registry = create_tool_registry(name, workspace=f"/workspace/{name}", ...)
        loop = AgentLoop(config=config, models=models, tool_registry=tool_registry, ...)
        heartbeat = Heartbeat(agent_name=name, agent_loop=loop, ...)
        channels = setup_channels(config, loop, agent_env=agent_env, ...)
        runners.append((name, loop, heartbeat, channels))

    # Start all concurrently
    for name, loop, heartbeat, channels in runners:
        await heartbeat.start()
    await asyncio.gather(*[channels.start_all() for _, _, _, channels in runners])
```

### Dockerfile — Single image

```dockerfile
FROM inotagent-base
COPY agents/ /app/agents/
```

### `load_agent_env()` — New helper (~30 lines)

Reads `agents/{name}/.env` into a dict. Channels and tools use this dict instead of `os.environ.get()`.

### Browser singleton — Minor refactor

Make `BrowserTool` share a single Playwright instance across all agents instead of creating one per agent.

---

## What Doesn't Change

- `AgentLoop` — already an independent class
- `loop.py` — unchanged
- `tools/` — unchanged (scoped by agent_name)
- `db/` — unchanged (pool is singleton, queries scoped by agent_name)
- `llm/` — unchanged (stateless clients)
- `channels/` — unchanged (each agent gets own ChannelManager)
- `config/` — unchanged (loads per agent dir)
- `skills`, `agent_configs`, `memories` — all scoped by agent_name in DB

---

## Sub-Agents (Ephemeral Specialists)

On top of multi-agent containers, agents can spawn **sub-agents** — temporary, focused LLM calls that use a specific skill as their system prompt.

### How It Works

```
Robin is working on a coding task
        ↓
Robin decides: "I should review this code before committing"
        ↓
Tool call: delegate(skill="code_review", task="Review this diff:\n...")
        ↓
System loads code_review skill from DB
        ↓
Single LLM call: system=skill.content, user=task (no tools, no history)
        ↓
Returns review result to Robin
        ↓
Robin incorporates feedback and continues
```

### Implementation: `delegate` Tool (~50 lines)

```python
DELEGATE_TOOL = {
    "name": "delegate",
    "description": "Delegate a task to a specialist sub-agent. Uses a specific skill as its expertise.",
    "input_schema": {
        "type": "object",
        "properties": {
            "skill": {"type": "string", "description": "Skill name to use as expertise"},
            "task": {"type": "string", "description": "The task or question"},
            "model": {"type": "string", "description": "Optional: model override (default: parent's model)"},
        },
        "required": ["skill", "task"],
    },
}

async def delegate(self, skill: str, task: str, model: str | None = None) -> str:
    from inotagent.db.skills import load_skill_by_name
    skill_data = await load_skill_by_name(skill)
    if not skill_data:
        return f"Error: Skill '{skill}' not found."

    model_id = model or self.config.model_id
    response = await chat_with_fallback(
        models=self.models,
        model_id=model_id,
        fallbacks=self.config.fallbacks,
        system=skill_data["content"],
        messages=[LLMMessage(role="user", content=task)],
        max_tokens=2048,
    )
    return response.content
```

### Sub-Agent vs Multi-Agent

| | Multi-Agent | Sub-Agent |
|---|---|---|
| Lifetime | Permanent (runs in container) | Ephemeral (single LLM call) |
| Identity | Full agent (name, persona, Discord bot) | None (just a skill) |
| Memory | Has own memories + history | None (stateless) |
| Channels | Own Discord/Slack/Telegram | None (parent handles) |
| Tools | Full toolset (19+ tools) | None (LLM only, v1) |
| Heartbeat | Own heartbeat | None |
| Use case | Team member | Temporary specialist |
| Cost | Shared container overhead | One LLM call |

### Future: Sub-Agents With Tools

```python
delegate(skill="code_review", task="...", tools=["read_file", "search_files"])
```

Allows sub-agent to gather its own context. Adds tool registry scoping complexity.

---

## Trade-offs

### Pros
- **Resource efficiency**: One DB pool, one browser, one embedding client — shared across N agents
- **Memory savings**: ~64 MiB total instead of ~64 MiB × N containers
- **Flexible deployment**: Same image supports all-in-one, team split, or 1:1
- **Sub-agents**: Lightweight delegation to specialist skills — one LLM call
- **Simpler scaling**: Add agent = add folder + env file, change `AGENTS` var

### Cons
- **Blast radius**: One agent's crash/memory leak affects all agents in container
- **Log interleaving**: All agents log to same stdout (mitigated by `[agent_name]` prefix)
- **No independent restart**: Restarting one agent requires restarting the container (mitigated by `restart_requested` DB flag for per-agent loop restart)

### Mitigations
- **Crash isolation**: Wrap each agent's channel loop in `try/except`, log error, continue others
- **Agent health**: Heartbeat per agent reports independently — stale heartbeat = detectable issue
- **Graceful per-agent restart**: `restart_requested` flag restarts specific agent's loop without killing process
- **Per-agent logging**: Already prefixed with `[agent_name]`

---

## Implementation Steps

### Phase 1: Multi-agent container
1. Add `load_agent_env()` helper — reads per-agent `.env` into dict (~30 lines)
2. Refactor `main.py` — multi-agent mode with `--agents` flag (~100 lines)
3. Refactor channels to accept env dict instead of `os.environ` (~20 lines)
4. Make BrowserTool a shared singleton (~10 lines)
5. Per-agent workspace dirs (~5 lines)
6. Single Dockerfile with all agents
7. Update docker-compose.yml with `AGENTS` env var
8. Tests

### Phase 2: Sub-agents
1. Add `load_skill_by_name()` to `db/skills.py` (~10 lines)
2. Add `delegate` tool definition + handler (~50 lines)
3. Register in `setup.py` (~3 lines)
4. Tests

### Phase 3: Cleanup
1. Remove per-agent Dockerfiles (optional — can keep for minimal images)
2. Update docs (CLAUDE.md, README, project_summary)

---

## Estimated Effort

| Phase | Lines | Time |
|---|---|---|
| Phase 1: Multi-agent | ~165 lines changed | 1 day |
| Phase 2: Sub-agents | ~65 lines new | Half day |
| Phase 3: Cleanup | ~30 lines docs | 1 hour |
| **Total** | **~260 lines** | **~2 days** |


## Status: DONE
