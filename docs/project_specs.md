# OpenVAIA — Technical Specs

Setup, configuration, architecture, and technical reference. For project overview, see `project_summary.md`.

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/inotives/openvaia.git
cd openvaia
```

### 2. Bootstrap environment files

```bash
make bootstrap
```

This creates `.env` files from templates. Edit them:

**`.env`** — Postgres connection:
```env
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=inotives
POSTGRES_PASSWORD=<your-password>
POSTGRES_DB=inotives
PLATFORM_SCHEMA=openvaia
```

**`agents/ino/.env`** — Agent credentials (same structure for each agent):
```env
NVIDIA_API_KEY=<your-nvidia-key>
DISCORD_BOT_TOKEN=<your-discord-bot-token>
GITHUB_TOKEN=<fine-grained PAT for gh CLI>
GITHUB_TOKEN_PATS=<classic PAT for git push>
```

> Only the API key for the model in `agent.yml` is required. Default is `nvidia-minimax-2.5` so you need `NVIDIA_API_KEY`.

### 3. Configure channels (optional)

Edit `agents/ino/agent.yml` to set up communication channels:

```yaml
model: nvidia-minimax-2.5
fallbacks:
  - nvidia-minimax-2.1

channels:
  discord:
    enabled: true
    allowFrom: ["YOUR_DISCORD_USER_ID"]
    guilds:
      "YOUR_GUILD_ID":
        requireMention: true
  slack:
    enabled: false          # Requires SLACK_BOT_TOKEN + SLACK_APP_TOKEN
  telegram:
    enabled: false
    allowFrom: ["YOUR_TELEGRAM_USER_ID"]  # Required — without this, anyone can message the bot
```

Each channel requires its own credentials in the agent's `.env` file. Discord IDs: Settings > Advanced > Developer Mode, then right-click to copy.

### 4. Deploy

**With local Postgres** (first time, or no existing Postgres):
```bash
make deploy-all              # All agents
make deploy-all AGENT=ino    # Just ino
```

**With existing Postgres** (already running a Postgres instance):
```bash
make deploy AGENT=ino
```

### 5. Verify

```bash
# Check container status
make ps

# Watch logs
make logs AGENT=ino
```

You should see:
```
=== inotagent boot: ino ===
Configuring git credentials...
Database inotives already exists
Migrations applied successfully
Running bootstrap...
Agent 'ino' registered
Bootstrap complete for 'ino'
Starting inotagent for ino...
Agent 'ino' initialized with model 'nvidia-minimax-2.5' (22 tools, db=yes)
Heartbeat started for ino
Discord connected: ino#0021
```

---

## Local Development (without Docker)

Agents can run natively on the host machine instead of Docker. Same Postgres, same data — just different execution environment.

**Prerequisites:** Python 3.12, uv, dbmate, Postgres running (Docker or local)

```bash
make db                      # start Postgres (Docker)
make local-setup             # first time: install deps + migrate + seed
make local-run AGENT=ino     # run single agent
make local-run-multi         # run multi-agent (AGENTS=ino,robin)
make local-stop              # stop local agents
```

**When to use local instead of Docker:**
- GPU access needed (ML training, video processing)
- Native display needed (Godot, headed Chrome, desktop automation)
- Native app integration (FFmpeg, audio tools)
- Faster iteration during development (no rebuild)

**Shared state:** Docker and local agents share the same Postgres — conversations, memories, skills, tasks are all shared. Do NOT run the same agent in Docker AND locally simultaneously.

**Hybrid deployment:** Run standard agents (ino, robin) in Docker, special agents (with GPU/display needs) locally — all sharing the same DB.

---

## Boot Sequence (Docker)

Supports multi-agent mode where bootstrap runs per agent, then inotagent starts with `--agents ino,robin` (defined in `inotagent/entrypoint.sh`):

```
1. Git credentials     — configure GITHUB_TOKEN_PATS for push, set user.name + user.email
2. Ensure database     — create POSTGRES_DB if not exists (psycopg)
3. Run migrations      — dbmate applies infra/postgres/migrations/ with PLATFORM_SCHEMA substitution
4. Bootstrap (per agent) — python3 -m inotagent.bootstrap:
                           • Register agent in platform.agents
                           • Seed agent_configs from agent.yml (ON CONFLICT DO NOTHING)
                           • Create #tasks and #public spaces
                           • Add all agents as members
                           • Announce boot in #public
                           • Announce pending tasks in #tasks
                           • Clone/pull assigned repos to /workspace/repos/
5. Start inotagent     — python3 -m inotagent --agents ino,robin:
                           • Init async Postgres pool
                           • Load per-agent config and env (agent.yml + models.yml + platform.yml)
                           • Apply DB config overrides (agent_configs table)
                           • Load skills from DB (skills + agent_skills tables)
                           • Build system prompt (AGENTS.md + TOOLS.md + skills + model info)
                           • Count system prompt tokens (stored in agent_configs)
                           • Create tool registry (22 tools)
                           • Start heartbeat with recurring task scheduling (60s health + task/message/mission detection)
                           • Connect channels (Discord, Slack, Telegram as configured)
                           • Enter channel mode (await messages)
```

---

## Project Structure

```
openvaia/
├── docker-compose.yml
├── Dockerfile.agents               # Multi-agent container image
├── .env / .env.template
├── Makefile
│
├── inotagent/                     # Custom agent runtime
│   ├── Dockerfile                 # Base image: python:3.12-slim + tools
│   ├── entrypoint.sh              # Container boot sequence
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── skills/                    # Skill files (81: 3 global + 78 non-global), imported via make import-skills
│   └── src/inotagent/
│       ├── main.py                # Entry point (CLI, one-shot, channel modes)
│       ├── loop.py                # Core reasoning loop (LLM → tools → response)
│       ├── bootstrap.py           # One-time setup (register, spaces, repos)
│       ├── __main__.py            # python -m inotagent support
│       ├── config/                # Config loaders (YAML + DB override)
│       ├── llm/                   # Multi-provider LLM client + embedding client
│       │   ├── anthropic.py       # Anthropic SDK client
│       │   ├── openai_compat.py   # OpenAI-compatible (NVIDIA, Groq, etc.)
│       │   ├── embeddings.py      # Embedding client (NVIDIA NIM)
│       │   ├── factory.py         # Provider selection + fallback
│       │   └── tokens.py          # Token counting + context management
│       ├── tools/                 # Tool system
│       │   ├── registry.py        # Tool registry + dispatch
│       │   ├── shell.py           # Shell command execution
│       │   ├── files.py           # File operations (read, list, search)
│       │   ├── browser.py         # Web browsing (playwright)
│       │   ├── discord_tool.py    # Proactive Discord messaging
│       │   ├── platform.py        # Tasks + messaging (Postgres-backed)
│       │   ├── memory.py          # Memory store/search (hybrid FTS + pgvector embedding)
│       │   ├── research.py        # Research report store/search/get
│       │   └── setup.py           # Wire all 22 tools into registry
│       ├── channels/              # Communication channels
│       │   ├── discord.py         # Discord bot (discord.py)
│       │   ├── slack.py           # Slack bot (slack-bolt, Socket Mode)
│       │   ├── telegram.py        # Telegram bot (python-telegram-bot)
│       │   └── base.py            # Channel interface
│       ├── db/                    # Async Postgres layer
│       │   ├── pool.py            # Connection pool (psycopg3)
│       │   ├── conversations.py   # Conversation history CRUD
│       │   ├── memory.py          # Memory storage + hybrid search (FTS + embedding)
│       │   ├── research.py        # Research report storage + search
│       │   ├── skills.py          # Agent skills loader (DB-driven)
│       │   └── agent_configs.py   # Runtime config overrides (DB-driven)
│       └── scheduler/             # Background services
│           └── heartbeat.py       # Health check, task/message/mission detection, recurring task scheduling
│
├── agents/
│   ├── _template/                 # Agent scaffolding template
│   ├── ino/                       # Global Financial Researcher
│   │   ├── AGENTS.md              # Identity + role + operating manual
│   │   ├── TOOLS.md               # Environment notes
│   │   ├── agent.yml              # Model + channel config
│   │   ├── Dockerfile             # Extends inotagent-base
│   │   └── .env / .env.template
│   └── robin/                     # Trading Operations Engineer
│       └── (same structure)
│
├── ui/                            # Next.js + Ant Design admin dashboard
├── infra/postgres/migrations/     # dbmate SQL migrations
├── resources/                     # Shared resources (gitignored)
├── tests/                         # Project integrity tests
└── scripts/
    ├── bootstrap.sh               # Env file generator
    ├── create-agent.sh            # New agent scaffolding from _template
    ├── task.sh                    # Task management CLI
    ├── repo.sh                    # Repo assignment CLI
    ├── import-skills.py            # Skill import tool
    └── schema_dev.sh              # Dev schema testing utility
```

---

## Agents

### ino (Global Financial Researcher)

Market and data research agent. Investigates APIs, data sources, crypto/DeFi/equities markets, and technical topics. Delivers structured reports stored in the research database.

- **Model**: nvidia-minimax-2.5 → fallbacks: nvidia-minimax-2.1, nemotron-3-super
- **Primary tool**: browser (web research)
- **Mission tags**: research, crypto, market, defi, api, data
- **Channels**: Discord, Slack, Telegram
- **Personality**: Analytical, thorough, data-driven

### robin (Trading Operations Engineer)

Trading operations and development. Handles trading system code, data pipelines, strategy implementation, and infrastructure. Receives tasks from Boss or picks them up from the mission board.

- **Model**: nvidia-minimax-2.5 → fallbacks: nvidia-minimax-2.1, nemotron-3-super
- **Primary tools**: read_file, write_file, shell (direct coding)
- **Mission tags**: trading, crypto, data, coding, testing
- **Channels**: Discord
- **Personality**: Direct, concise, action-oriented

---

## Workspace Files

Each agent's persona is defined in markdown files:

| File | Purpose |
|---|---|
| `AGENTS.md` | Identity, role, workflows (task, git, DB, repo), operational rules, red lines |
| `TOOLS.md` | Environment setup (paths, all 20 available tools with examples) |
| `agent.yml` | Model selection, fallbacks, channel config, mission tags |

Memory is stored in Postgres (not files) and accessed via the `memory_search` tool. Memory search uses hybrid ranking — keyword matching (Postgres FTS) weighted 30% + semantic similarity (pgvector embeddings) weighted 70% — so agents find relevant memories even without exact keyword overlap. Research reports are stored separately via `research_store` and searchable by any agent.

---

## Admin UI

A Next.js + Ant Design dashboard for managing the platform. Runs as a Docker container on port `7860`.

```bash
make ui          # build + start the UI
make ui-logs     # tail logs
```

Open http://localhost:7860 to access the dashboard.

### Pages

| Page | What it does |
|---|---|
| **Dashboard** | Agent status (online/offline), task summary counts, recent messages |
| **Tasks** | Kanban board (6 columns by status) with filters, detail drawer, create/update |
| **Agents** | Agent list with detail page (Overview, Chat, Skills, Repos, Tasks, Research, Memory, Memory Graph, Settings) |
| **Skills** | Skill registry with keyword-based icons, tag/description display |
| **Resources** | Shared resource management (add, search, browse) |
| **Prompt Gen** | Prompt generation and testing tools |
| **Config** | View/edit/delete `platform.config` rows |

### Agent Detail Page

Each agent has a comprehensive detail page with tabs:

| Tab | What it does |
|---|---|
| **Overview** | Status, model info, health metrics |
| **Chat** | Direct chat with the agent via web channel |
| **Skills** | Agent's assigned skills with icons |
| **Repos** | Assigned git repositories |
| **Tasks** | Filtered task list (status, priority, tag, date range, search) with sort |
| **Research** | Research reports with title search, tag filter, date range |
| **Memory** | Agent's stored memories |
| **Memory Graph** | Visual memory relationship graph |
| **Settings** | Runtime config: model, fallbacks, mission tags, parallel (DB-backed, no redeploy) |

### Gamified Office (`/office`)

A 2D pixel art office view built with PixiJS v8. Agents are visualized as animated NPCs walking around a multi-floor building, moving between rooms based on their current activity.

| Room | Floor | Purpose |
|---|---|---|
| **Resting** | F-1 (left) | Default room when agent is idle |
| **Research** | F-1 (right) | Agent doing research, search, or analysis |
| **Trading** | F-2 (left) | Agent working on trading, markets, or pricing |
| **Office** | F-2 (right) | General work (active but no keyword match) |

**Features:**
- Animated NPC sprites with walk cycles, click to open agent panel
- Interactive doors (click to swing open/close) and elevator buttons (click to open doors)
- LED dot-matrix floor indicators and rooftop company sign
- Dynamic room assignment — polls agent tasks + busy status + chat keywords every 10s
- Agent panel with tabs: Profile, Chat, Skills (equip/unequip), Research (report viewer), Memory
- Pixel art assets from [Pixel Spaces](https://netherzapdos.itch.io/pixel-spaces) + custom PIXI.Graphics drawn objects

**Architecture:**
```
office/components/
  OfficeCanvas.tsx     — React canvas + agent rendering/animation
  BuildingScene.ts     — Skyline, building frame, orchestrates floors
  Floor1.ts            — Resting + Research room furniture
  Floor2.ts            — Trading + Office room furniture
  ElevatorZone.ts      — Shared elevator drawing + button animation
  officeTypes.ts       — Constants, types, texture loading
  AgentPanel.tsx       — Agent interaction panel (chat, skills, research, memory)
  pixelObjects/        — Categorized drawn furniture (office, wall, infrastructure, appliances, decorations)
```

### Authentication

NextAuth.js-based authentication with two providers:

- **Google OAuth** (recommended for internet-facing deployments) — set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_ALLOWED_EMAILS` to restrict access by email
- **Username/Password** (for local deployments) — set `UI_USERNAME` and `UI_PASSWORD`

Both providers are optional and can be used together. If neither is configured, the UI shows a configuration error on the login page.

---

## Task Management

A lightweight Jira-like system built into Postgres for agent coordination.

- Auto-generated keys: `INO-001`, `ROB-002`
- Parent/subtask hierarchy
- Status workflow: `backlog` → `todo` → `in_progress` → `review` → `done` (or `blocked`)
- Priority levels: `critical`, `high`, `medium`, `low`
- Agents interact via tool calls: `task_create()`, `task_update()`, `task_list()`
- Humans manage via the Admin UI kanban board or CLI: `make task-list`, `make task-create`

### Mission Board

When agents are idle, they check the **mission board** — unassigned backlog tasks tagged with topics. Agents self-select missions matching their `mission_tags` in `agent.yml`.

```bash
# Create a mission (no TO= means backlog, agents auto-pickup by matching tags)
make task-create TITLE="Research DeFi yield aggregators" BY=boss TAGS=research,defi

# Create an assigned task (direct assignment)
make task-create TITLE="Fix login bug" BY=boss TO=robin PRIORITY=high
```

Flow: Boss creates mission → heartbeat detects matching tags → agent self-assigns → executes → reports to Discord.

---

## Model Configuration

Models are defined in `inotagent/models.yml` with token limits per model. Each agent selects its model and fallbacks in `agent.yml`.

**Config resolution**: `agent.yml` (initial seed) → `agent_configs` DB table (runtime overrides) → `platform.yml` default → first in registry.

At first boot, `agent.yml` values are seeded into the `agent_configs` table with `ON CONFLICT DO NOTHING`. After that, changes made via the UI Settings tab or direct DB updates persist across redeploys without being overwritten.

**Overridable via DB**: model, fallbacks, mission_tags, parallel.
**YAML only**: channels (infrastructure config, not overridable via DB).

**`agent.yml` example:**
```yaml
model: nvidia-minimax-2.5
fallbacks:
  - nvidia-minimax-2.1
mission_tags:
  - coding
  - testing
```

**`models.yml` fields per model:**
| Field | Purpose | Example |
|---|---|---|
| `context_window` | Max input tokens | `200000` |
| `max_tokens` | Max output tokens per response | `16384` |

Fallback models auto-activate on rate limit (429) or other errors.

---

## Skills

Skills are stored in the `skills` and `agent_skills` tables. Each skill has a name, description, content (markdown), and tags. 81 skill files (3 global + 78 non-global) live in `inotagent/skills/` and are imported via `make import-skills`. Skills are loaded into the agent's system prompt at startup and refreshed every heartbeat cycle (60s).

Manage skills via the Admin UI Skills page or Agent Detail → Skills tab.

---

## Makefile Commands

```
# Deployment
make deploy [AGENT=name]     Build + start agents
make deploy-all              Build + start with local Postgres
make start [AGENT=name]      Start existing containers
make stop [AGENT=name]       Stop containers
make restart [AGENT=name]    Restart containers
make db                      Start only Postgres (no agents or UI)
make down                    Tear down everything

# Monitoring
make ps                      Show running services
make logs [AGENT=name]       Docker logs
make shell AGENT=name        Shell into container

# Admin UI
make ui                      Build + start admin UI (port 7860)
make ui-logs                 Admin UI logs

# Task management
make task-list [AGENT= STATUS=]  List tasks (filterable)
make task-get KEY=INO-001    Show task details
make task-create TITLE=...   Create task (BY=, TO=, REPO=, PRIORITY=, TAGS=)
make task-create TITLE=... BY=boss TAGS=research,crypto  Mission (backlog)
make task-update KEY=...     Update task (STATUS=, RESULT=)
make task-summary [AGENT=]   Task counts by status
make task-board              Kanban view

# Repo management
make repo-list [AGENT=]      List repo assignments
make repo-add URL=... NAME=... TO=... BY=...  Assign repo
make repo-remove URL=... AGENT=...  Remove assignment
make repo-agent AGENT=name   Show agent's repos

# Testing
make build                   Build images only
make test                    Run project integrity tests
make inotagent-test          Run inotagent unit tests (350 tests)
make bootstrap               Generate .env from templates
make import-skills           Import skill files from inotagent/skills/
```

---

## Adding a New Agent

### Step 1: Create from template

```bash
make create-agent NAME=alex EMAIL=alex@yourdomain.com
```

This scaffolds `agents/alex/` from `agents/_template/` with the agent name substituted.

### Step 2: Customize the persona

Edit the workspace files to define who this agent is:

| File | What to change |
|---|---|
| `AGENTS.md` | Name, emoji, personality, role, workflows, operational rules, peer agents, red lines |
| `TOOLS.md` | Usually no changes needed |

### Step 3: Configure the agent

**`agents/alex/agent.yml`** — set the model, mission tags, and channels:
```yaml
model: nvidia-minimax-2.5
fallbacks:
  - nvidia-minimax-2.1

mission_tags:
  - coding
  - testing

channels:
  discord:
    enabled: true
    allowFrom: ["YOUR_DISCORD_USER_ID"]
    guilds:
      "YOUR_GUILD_ID":
        requireMention: true
```

> Each agent needs its own Discord bot if you want it on Discord.

### Step 4: Update the Dockerfile

**`agents/alex/Dockerfile`**:
```dockerfile
FROM inotagent-base

COPY agents/alex/agent.yml /app/agents/alex/agent.yml
COPY agents/alex/AGENTS.md /app/agents/alex/AGENTS.md
COPY agents/alex/TOOLS.md /app/agents/alex/TOOLS.md
COPY agents/alex/AGENTS.md /workspace/AGENTS.md
```

### Step 5: Set up credentials

**`agents/alex/.env`** (copy from `.env.template`):
```env
GIT_EMAIL=alex@yourdomain.com
NVIDIA_API_KEY=<your-key>
DISCORD_BOT_TOKEN=<alex-bot-token>
GITHUB_TOKEN=<fine-grained PAT for gh CLI>
GITHUB_TOKEN_PATS=<classic PAT for git push>
```

### Step 6: Add to docker-compose.yml

Copy an existing agent service block and change the name:

```yaml
alex:
  build:
    context: .
    dockerfile: agents/alex/Dockerfile
  container_name: agent_alex
  env_file:
    - .env
    - agents/alex/.env
  environment:
    AGENT_NAME: alex
    PLATFORM_SCHEMA: ${PLATFORM_SCHEMA:-platform}
    POSTGRES_HOST: ${POSTGRES_HOST:-postgres}
    POSTGRES_PORT: ${INTERNAL_POSTGRES_PORT:-5432}
  volumes:
    - alex_workspace:/workspace
  depends_on:
    postgres:
      condition: service_healthy
      required: false
  networks:
    - platform
  healthcheck:
    test: ["CMD-SHELL", "kill -0 1"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 30s
  deploy:
    resources:
      limits:
        cpus: "1.0"
        memory: 2g
```

Don't forget to add `alex_workspace:` to the `volumes:` section at the bottom.

### Step 7: Deploy

```bash
make deploy AGENT=alex
```

The boot sequence will automatically register the agent, create spaces, sync repos, and connect Discord.

### Step 8: Tell existing agents about the new peer

Update `AGENTS.md` for agents that need to know about the new team member:

```markdown
## Peer Agents
- **robin** (worker) — coding, research, system tasks
- **alex** (worker) — whatever alex specializes in
```

---

## Roadmap

### v0
- [x] Project structure and conventions
- [x] Platform schema (spaces, messages, agents, config, tasks)
- [x] Central model registry (6 providers, 20+ models)
- [x] Discord integration
- [x] Health monitoring
- [x] Task management system
- [x] Admin UI with kanban board
- [x] Agent deployed: ino, robin (live on Discord)

### v1 (Current — inotagent)
- [x] Custom async Python runtime
- [x] Multi-provider LLM client (Anthropic + OpenAI-compat)
- [x] Tool system (22 tools: shell, files, browser, discord_send, tasks, messaging, memory, research)
- [x] Async Postgres persistence (conversations, memory with hybrid FTS + embedding search, research reports)
- [x] Context window management (sliding window truncation)
- [x] Heartbeat with recurring task scheduling + mission board
- [x] Docker packaging (python:3.12-slim, ~825 MB image, ~64 MiB runtime)
- [x] Clean migration from previous runtime (no data retention needed)
- [x] Role differentiation: ino (researcher), robin (coder)
- [x] Discord proactive notifications (discord_send tool)
- [x] Research report storage and search (research_store/search/get)
- [x] Mission board (idle agents self-select backlog tasks by tags)
- [x] Next.js + Ant Design admin UI (replaced Gradio)
- [x] Agent detail page (chat, skills, repos, tasks, research, memory, settings)
- [x] DB-driven skills system (skills + agent_skills tables, refreshed per heartbeat)
- [x] Runtime-configurable agent settings via `agent_configs` table (model, fallbacks, mission_tags, parallel)
- [x] Recurring tasks with schedule tags (replaced cron_jobs)
- [x] Task/research filtering (status, priority, tags, date range, search)
- [x] 350 unit tests
- [x] End-to-end task delegation workflow (human→agent, agent→agent with review verification)
- [x] Multi-channel support: Discord, Slack (Socket Mode), Telegram (with allowFrom security)
- [x] Agent template system (`agents/_template/` + `make create-agent`)
- [x] System prompt token counting at boot (stored in `agent_configs`)
- [x] Role specialization: ino (Global Financial Researcher), robin (Trading Operations Engineer)
- [x] Trading operations skill (data health, cycle monitoring, asset management)
- [x] Platform config editor in Admin UI
- [x] Skill search/filter in Admin UI
- [x] Lazy tab loading for agent detail page performance
- [x] Agent self-improvement via `self_improvement` skill (memory-backed learning from feedback)
- [x] pgvector embedding-based memory search (hybrid FTS + semantic via NVIDIA NIM embeddings)
- [x] Multi-agent container model (shared infrastructure, per-agent env loading)
- [x] Sub-agent delegation via `delegate` tool
- [x] Resource management (resource_search, resource_add tools + `resources` table)
- [x] Email sending via `send_email` tool
- [x] Skill creation from agent context via `skill_create` tool
- [x] 81 skill files (3 global + 78 non-global) with `make import-skills`

### v1.3 — Gamified Office UI
- [x] 2D pixel art office with PixiJS v8 (client-side rendering in Next.js)
- [x] Multi-floor building with rooms: Resting, Research, Trading, Office
- [x] Animated NPC agents with walk cycles, click to interact
- [x] Dynamic room assignment based on agent activity (tasks, busy status, chat keywords)
- [x] Interactive doors (swing open/close) and elevator buttons
- [x] Agent panel: Chat (stable sessions), Skills (equip/unequip), Research (report viewer), Memory
- [x] Pixel art sprites from Pixel Spaces + custom PIXI.Graphics drawn objects
- [x] Modular architecture: BuildingScene, Floor1/2, ElevatorZone, pixelObjects/

### v1.4 — Proactive Agents + Self-Evolving Skills
- [x] Proactive agent behavior — recurring tasks, idle behavior skill, heartbeat idle detection (ES-0009)
- [x] Human message priority interrupt — autonomous tasks pause for human messages
- [x] Seed script for recurring tasks (`make seed-tasks`)
- [x] Self-evolving skills — `skill_propose` tool (FIX/DERIVED/CAPTURED), human approval flow (ES-0010)
- [x] Skill quality metrics tracking (per-agent, per-skill: selected, applied, completed, fallback)
- [x] Skill version history with lineage (origin, generation, parent tracking)
- [x] Skill evolution proposals API (list, get, approve/reject with auto-apply)
- [x] 103 skills (5 global + 98 non-global) from 5 sources (community, superpowers, gstack, openspec, platform)
- [x] Spec-driven development skills (ES-0013): proposal, requirement spec, technical design, verification
- [x] Document tagging convention (PROP:/SPEC:/DESIGN:/VERIFY:)
- [x] Global development_workflow skill — routes agents to correct workflow by complexity

### v1.5 — Dynamic Skill Equipping (ES-0014)
- [x] Skill chains DB + 12 default chains (coding, bugfix, research, security, ops, trading)
- [x] Task-aware dynamic skill loading with chain matching + phase progression
- [x] Human approval gates for chain steps
- [x] Skill usage metadata recording + skill_equip tool (#22)
- [x] Token budget 9000, deduplication, static skill fallback

### v2 (DRAFTs)
- [ ] Production deployment (internet-facing hosting)
- [ ] Parallel execution (concurrent tool calls)
- [ ] Robin trading toolkit — agent-first CLI tools for autonomous crypto trading (ES-0012)
