# OpenVAIA — Open Visio AI Agents

Dockerized multi-agent AI platform powered by **inotagent** — a custom async Python runtime.

---

## Core Concept

**Container = Company. Agent = Worker.**

- A **container** is the company — it provides the infrastructure (shell, files, browser, channels, memory, LLM). Multiple agents can share one container or run 1:1.
- An **agent** is a worker within that company — it has a name, a personality, its own credentials (GitHub account, Discord bot, etc.), and its own way of working.
- Agents can **delegate** work to other agents via the `delegate` tool, enabling sub-agent workflows within a container.
- All agents share the same base image and toolset. Each agent picks their own brain (LLM model) from a central registry.

---

## Design Philosophy

**inotagent-first, runtime-pluggable** — inotagent is the default and primary runtime, but the architecture deliberately separates agents from the engine:

- `inotagent/` is the **default runtime engine** — the async Python code, base Docker image, config files, and tests. It provides the LLM client, tool system, channels, persistence, and scheduling.
- `agents/` are the **deployable individuals** — each with their own identity (AGENTS.md), tool rules (TOOLS.md), model preferences (agent.yml), credentials (.env), and Dockerfile.

Agents are *consumers* of the runtime, not part of it. An agent's Dockerfile simply extends the runtime's base image (`FROM inotagent-base`), and the rest is identity and config.

This separation enables support for **alternative runtimes** (OpenClaw, ZeroClaw, etc.). To use a different engine:
1. Build the alternative runtime's base image
2. Update agent Dockerfiles to `FROM <runtime-base>` (e.g. `FROM openclaw-base`)
3. Adapt `agent.yml` if the config schema differs

Agent identity files (AGENTS.md, TOOLS.md) and credentials (.env) carry over unchanged. The agents don't care what office they walk into — they just need a desk and a brain.

---

## Runtime

- **Core runtime**: inotagent — custom async Python agent runtime (in `inotagent/`)
- **Base image**: `python:3.12-slim` + git, gh, dbmate, uv
- **Package manager**: uv (pyproject.toml + uv.lock)
- **Database**: Postgres with pgvector (`pgvector/pgvector:pg16`)
- **Migrations**: dbmate (platform schema, in `infra/postgres/migrations/`)
- **Coding tools**: Native tools (read_file, write_file, shell)
- **Channels**: Discord (discord.py), Slack (slack-bolt), Telegram (python-telegram-bot)

---

## Model Selection

Models are defined centrally in `inotagent/models.yml` with token limits (`context_window`, `max_tokens`) and selected per agent in `agent.yml`.

**Resolution order**: `agent.yml` model → DB `agent_configs` override → `inotagent/platform.yml` default_model → first model in registry

**Runtime overrides**: The `agent_configs` table stores per-agent overrides (model, fallbacks, mission_tags, parallel). `agent.yml` values are seeded on first boot with `ON CONFLICT DO NOTHING` — subsequent changes via UI or DB persist across redeploys. Channels remain YAML-only (infrastructure config).

**Fallbacks**: Each agent can specify fallback models in `agent.yml`. On rate limit (429) or error, inotagent automatically retries with the next fallback.

Providers without API keys set in the environment are automatically skipped — no startup failures for unused providers.

---

## Communication

- **Agent-to-agent**: Postgres `platform` schema — structured coordination, audit trail, queryable history
  - `public` space — all agents can talk here by default
  - `tasks` space — task coordination channel
  - `room` spaces — group channels, only members receive messages
  - `direct` spaces — 1-1 between two agents
- **Agent-to-human**: Discord, Slack, Telegram
  - Each agent has its own bot credentials per channel (in `.env`)
  - Discord: thread support, typing indicators, message chunking, guild requireMention
  - Slack: Socket Mode, workspace-restricted by default
  - Telegram: allowFrom security (user ID whitelist required)
  - Discord #tasks channel for human-facing updates

---

## Architecture

inotagent is a fully async Python runtime with shared infrastructure and per-agent environment loading. Multiple agents can run in a single container with `--agents ino,robin`, each loading their own `.env` and `agent.yml`:

- **LLM client**: Multi-provider (Anthropic SDK native, OpenAI-compatible via httpx for NVIDIA NIM, Groq, etc.) + embedding client (NVIDIA NIM)
- **Tool system**: 20 native tools — shell, file ops, browser, Discord, task management, messaging, memory, research, resources, email, delegation, skill creation
- **Agent loop**: `prompt → LLM → tool calls → results → LLM → response` (with automatic chaining)
- **Channels**: Discord (discord.py), Slack (slack-bolt Socket Mode), Telegram (python-telegram-bot)
- **Persistence**: Async Postgres (psycopg3) — conversations, memory (hybrid FTS + pgvector embedding search), research reports, skills, agent configs
- **Scheduler**: Heartbeat with recurring task scheduling (60s health + work detection + skill refresh)
- **Bootstrap**: One-time setup (register agent, create spaces, clone repos, announce boot)

Agent identity is defined via workspace files (`AGENTS.md`, `TOOLS.md`) which are loaded as system prompt context. ~5.3K tokens overhead per request (system prompt ~3.4K + tool definitions ~1.9K).

---

## Folder Structure

```
openvaia/
│
├── docker-compose.yml              # Orchestrates infra + agent containers
├── Dockerfile.agents               # Multi-agent container image
├── .env                            # Global infra secrets (gitignored)
├── .env.template
├── pyproject.toml                  # Root Python dependencies (test tooling)
├── Makefile
│
├── inotagent/                      # Custom agent runtime (async Python)
│   ├── Dockerfile                  # Base image: python:3.12-slim + tools
│   ├── entrypoint.sh               # Boot: DB create → migrations → bootstrap → inotagent
│   ├── pyproject.toml              # Runtime Python dependencies
│   ├── uv.lock
│   ├── src/inotagent/
│   │   ├── main.py                 # Entry point (CLI, one-shot, channel modes)
│   │   ├── loop.py                 # Core agent reasoning loop
│   │   ├── bootstrap.py            # One-time setup (register, spaces, repos, announce)
│   │   ├── llm/                    # Multi-provider LLM client
│   │   ├── tools/                  # Tool registry + handlers (21 tools)
│   │   ├── channels/               # Discord, Slack, Telegram
│   │   ├── db/                     # Async Postgres (conversations, memory, research, skills, agent_configs)
│   │   ├── scheduler/              # Heartbeat with recurring task scheduling
│   │   └── config/                 # Agent, model, platform config (YAML + DB override)
│   ├── skills/                     # Skill files (81: 3 global + 78 non-global), imported via make import-skills
│   └── tests/                      # Unit tests (350 tests)
│
├── agents/                         # Each folder is a unique individual agent
│   ├── _template/                 # Agent scaffolding template
│   ├── robin/
│   │   ├── AGENTS.md               # Identity + role + operational rules
│   │   ├── TOOLS.md                # Tool documentation and usage examples
│   │   ├── agent.yml               # Agent config (model selection, fallbacks, mission_tags)
│   │   ├── Dockerfile              # Extends inotagent-base
│   │   ├── .env                    # Agent's personal credentials (gitignored)
│   │   └── .env.template
│   └── ino/
│       └── (same structure)
│
├── infra/
│   └── postgres/
│       └── migrations/             # dbmate platform schema migrations
│
├── tests/                          # Project integrity + UI tests
│   ├── test_project_integrity.py   # Validates project structure, config consistency
│   └── test_ui.py                  # Admin dashboard tests
│
├── ui/                             # Next.js + Ant Design admin dashboard
│
├── scripts/
│   ├── bootstrap.sh                # Generate .env files from templates
│   ├── create-agent.sh             # New agent scaffolding from _template
│   ├── task.sh                     # Task management CLI
│   ├── repo.sh                     # Repo assignment CLI
│   ├── import-skills.py             # Skill import tool
│   └── schema_dev.sh               # Dev schema testing utility
│
├── resources/                      # Shared resources (gitignored)
│
└── docs/
    └── project_summary.md          # This file
```

---

## Tool System (21 tools)

| Tool | Description |
|---|---|
| shell | Command execution with timeout |
| read_file | Read file contents |
| list_files | List directory with optional glob |
| search_files | Regex search across files |
| browser | Web page fetching via httpx |
| discord_send | Send messages to Discord channels |
| task_list | List/filter tasks from DB |
| task_create | Create new tasks |
| task_update | Update task status/assignment |
| send_message | Send platform messages to agent spaces |
| skill_create | Create new skills from agent context |
| resource_search | Search shared resources |
| resource_add | Add resources to the shared pool |
| send_email | Send emails from agent |
| delegate | Delegate work to sub-agents |
| memory_store | Store facts/preferences to Postgres (with embedding vector) |
| memory_search | Search memories by hybrid ranking (FTS keywords + semantic embedding) |
| research_store | Save full research reports (persistent, searchable) |
| research_search | Search research reports by keyword/tags |
| research_get | Retrieve full research report by ID |

---

## Skills System

Skills are reusable prompt modules stored in the `skills` table and assigned to agents via `agent_skills`. Each skill has:

- **name** — unique identifier
- **description** — short summary
- **content** — full markdown (appended to system prompt)
- **tags** — for filtering and keyword-based icon display

81 skill files (3 global + 78 non-global) live in `inotagent/skills/` and are imported via `make import-skills`.

Skills are loaded at startup and refreshed every heartbeat (60s). Manage via the Admin UI Skills page or Agent Detail → Skills tab.

---

## Task Workflow

**Human → Agent → Human**:
1. Boss creates task (Discord or `make task-create`)
2. Agent heartbeat detects pending task, picks it up
3. Agent works on it (coding via native tools, research via browser)
4. Agent sets status to `review` with PR link
5. Agent notifies Boss on Discord #tasks
6. Boss reviews and sets `done`

**Agent → Agent → Agent** (delegation):
1. Ino (researcher) creates task assigned to Robin (coder)
2. Robin's heartbeat picks it up, codes the solution
3. Robin sets status to `review`, notifies Ino via platform message + Discord
4. Ino's heartbeat detects delegated task in review
5. Ino reviews the PR, sets `done` if satisfactory or `todo` with feedback

**Mission Board** (self-service):
1. Boss creates unassigned backlog task with tags (`make task-create TITLE="..." BY=boss TAGS=research,defi`)
2. Agents with matching `mission_tags` in `agent.yml` auto-detect via heartbeat
3. Agent self-assigns and starts working

---

## Infrastructure

- **Postgres** (`pgvector/pgvector:pg16`) — single central instance
  - Shared database `inotives`, isolated by schema via `PLATFORM_SCHEMA` env var
  - Platform tables: `agents`, `spaces`, `space_members`, `messages`, `agent_status`, `config`, `tasks`, `agent_repos`, `conversations`, `memories`, `research_reports`, `resources`, `skills`, `agent_skills`, `agent_configs`
  - Supports both local Docker Postgres (`make deploy-all`) and external existing Postgres (`make deploy`)
- **dbmate** — database migration tool, runs platform migrations from `infra/postgres/migrations/`

---

## Agents (v1)

Each agent runs inotagent in its own container:

- **ino** (Global Financial Researcher) — investigates markets, APIs, data sources, equities and macro. Delivers structured reports. Delegates coding to other agents. Channels: Discord, Slack, Telegram.
- **robin** (Trading Operations Engineer) — handles trading system code, data pipelines, strategy implementation, and infrastructure. Channels: Discord.

---

## Boot Sequence

Defined in `inotagent/entrypoint.sh`. Supports multi-agent mode where bootstrap runs per agent, then inotagent starts with `--agents ino,robin`:

1. **Git credentials** — configure `GITHUB_TOKEN_PATS` for `git push`, set `user.name` + `user.email`
2. **Ensure database** — create `POSTGRES_DB` if not exists (via `psycopg`)
3. **Run migrations** — `dbmate` applies SQL from `infra/postgres/migrations/` with schema substitution
4. **Bootstrap (per agent)** — `python3 -m inotagent.bootstrap`: register agent, seed agent_configs from agent.yml, create spaces, add members, clone/pull repos, announce boot
5. **Start inotagent** — `exec python3 -m inotagent --agents ino,robin`: init DB pool, load per-agent config and env, load skills, count system prompt tokens, create tool registry (21 tools), start heartbeat with recurring task scheduling, connect channels (Discord/Slack/Telegram)

---

## What's Done (ES-0001 through ES-0010)

- [x] Custom async Python runtime (inotagent)
- [x] Multi-provider LLM client (Anthropic, OpenAI-compatible)
- [x] 21-tool system (shell, files, browser, Discord, tasks, messaging, memory, research, resources, email, delegation, skill creation, skill_propose)
- [x] Multi-channel: Discord (discord.py), Slack (slack-bolt), Telegram (python-telegram-bot)
- [x] Async Postgres persistence (conversations, memory with hybrid FTS + embedding search, research reports, resources)
- [x] Heartbeat with recurring task scheduling (health, task/mission/message detection, delegated review, skill refresh)
- [x] Recurring tasks with schedule tags (replaced cron_jobs)
- [x] Mission board (unassigned backlog + agent self-selection via tags)
- [x] Research report storage (full-text search + tag filtering)
- [x] Task delegation workflow (human→agent, agent→agent with review verification)
- [x] Agent-to-agent messaging (Postgres spaces)
- [x] Sub-agent delegation via `delegate` tool
- [x] Git repo management via `agent_repos` table
- [x] DB-driven skills system (98 skill files: 4 global + 94 non-global, imported via `make import-skills`)
- [x] Runtime-configurable agent settings via `agent_configs` table (model, fallbacks, mission_tags, parallel)
- [x] Next.js + Ant Design admin dashboard (Dashboard, Tasks, Agents, Skills, Resources, Prompt Gen, Config, Gamified Office)
- [x] Agent detail page (Overview, Chat, Skills, Repos, Tasks, Research, Memory, Memory Graph, Settings)
- [x] Task/research filtering (status, priority, tags, date range, search)
- [x] Dev schema testing workflow (`schema_dev.sh`)
- [x] CLI tools for task and repo management
- [x] 350 inotagent unit tests
- [x] Multi-agent container model (shared infrastructure, per-agent env loading)
- [x] Resource management (resource_search, resource_add tools + `resources` table)
- [x] Email sending via `send_email` tool
- [x] Skill creation from agent context via `skill_create` tool

- [x] Agent template system (`agents/_template/` + `make create-agent`)
- [x] System prompt token counting at boot (stored in `agent_configs`)
- [x] Role specialization: ino (Global Financial Researcher), robin (Trading Operations Engineer)
- [x] Trading operations skill
- [x] Platform config editor in Admin UI
- [x] Telegram allowFrom security (user ID whitelist)

- [x] Agent self-improvement via `self_improvement` skill (memory-backed learning from feedback)
- [x] pgvector embedding-based memory search (hybrid FTS + semantic via NVIDIA NIM embeddings)

### ES-0008 — Gamified Office UI (v1.3)
- [x] 2D pixel art office built with PixiJS v8 in Next.js (`/office` route)
- [x] Multi-floor building: F-1 (Resting + Research rooms), F-2 (Trading + Office rooms)
- [x] Animated NPC agents with walk cycles, moving between rooms based on activity
- [x] Dynamic room assignment — polls tasks, agent busy status, and chat keywords every 10s
- [x] Interactive elements: doors (swing open/close), elevator buttons (open doors on click)
- [x] Agent panel: Profile, Chat (stable daily sessions), Skills (equip/unequip), Research (report list + viewer), Memory
- [x] Modular architecture: BuildingScene, Floor1/2, ElevatorZone, pixelObjects/ (categorized drawn components)
- [x] Pixel art assets from [Pixel Spaces](https://netherzapdos.itch.io/pixel-spaces) + custom PIXI.Graphics objects
- [x] LED dot-matrix floor indicators, rooftop company sign, city skyline background

### ES-0009 — Proactive Agent Behavior (v1.4)
- [x] 8 recurring tasks for ino (market brief, alerts, resources) and robin (health check, ops log, retro, mission board)
- [x] Global `idle_behavior` skill — agents autonomously work when idle (mission board → stale research → resources → monitoring)
- [x] Heartbeat idle detection with configurable guardrails (proactive_enabled, proactive_max_daily, proactive_idle_minutes)
- [x] Human message priority interrupt — autonomous tasks pause between tool iterations for incoming human messages
- [x] Anti-repetition rules — agents check recent tasks before acting, no same work within 3 hours
- [x] Seed script for recurring tasks (`make seed-tasks`, hooked into `make clean-slate`)

### ES-0010 — Self-Evolving Skills (v1.4)
- [x] Skill quality metrics tracking — per-agent, per-skill: times_selected, times_applied, times_completed, times_fallback
- [x] Skill version history with lineage — origin (imported/fixed/derived/captured), generation, parent tracking
- [x] `skill_propose` tool (#21) — agents submit evolution proposals (FIX, DERIVED, CAPTURED)
- [x] Evolution proposals API — list, get, approve/reject with auto-apply (creates version + updates skill)
- [x] Updated daily review skill to use `skill_propose` instead of `skill_create`
- [x] DB migration 006: `skill_metrics`, `skill_versions`, `skill_evolution_proposals` tables
- [x] Phase 4-6 deferred pending observation (skill evolver agent, metric triggers, admin UI dashboard)

## What's Next (DRAFTs)

- [ ] Production deployment (internet-facing hosting)
- [ ] Parallel execution (concurrent tool calls)
- [ ] Robin trading toolkit — agent-first CLI tools for autonomous crypto trading (ES-0012)
