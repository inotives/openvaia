# OpenVAIA — Open Visio AI Agents

Dockerized multi-agent AI platform powered by **inotagent** — a custom async Python runtime. See `docs/project_summary.md` for full design.

## Key Concepts

- **Container = Company. Agent = Worker.** A container provides shared infrastructure (DB pool, browser, embedding). Agents are workers — each with own persona, credentials, model, skills.
- **inotagent** = custom async Python agent runtime. Handles LLM reasoning, tool execution, multi-channel communication, persistence, scheduling.
- **Multi-agent**: `AGENTS=ino,robin` runs multiple agents in one container. Or `AGENTS=ino` for single. Same image, different config.
- **Sub-agents**: `delegate` tool spawns ephemeral LLM calls using a skill as system prompt — for code review, security scan, etc.
- **Agent-to-agent** communication: Postgres `platform.messages` (structured coordination via spaces).
- **Agent-to-human** communication via Discord, Slack, Telegram, and Admin UI web chat.

## Design Philosophy

- **Runtime-pluggable**: inotagent is the default runtime, but agents (`agents/`) and runtime (`inotagent/`) are deliberately separated. Agents are consumers of the runtime, not part of it. Identity files (AGENTS.md, TOOLS.md, .env) are runtime-agnostic.
- **DB-driven skills**: 81 skill files in `inotagent/skills/` (3 global + 78 non-global). Imported via `make import-skills`. Stored in Postgres, injected into system prompt at startup and refreshed every heartbeat (60s). Skills can be edited via Admin UI without redeploy.
- **Skill file naming**: `0__<name>.md` = global (all agents), `1__<name>.md` = non-global (equip via UI). Token count shown in each file.
- **Hybrid memory search**: Postgres FTS (30%) + pgvector embeddings (70%). Falls back to FTS-only when embeddings unavailable.
- **Recurring tasks**: Replace cron — `schedule:daily@00:00`, `schedule:hourly`, `schedule:monthly@00:00` tags on tasks. Heartbeat resets completed tasks automatically.
- **Agent offline detection**: UI checks `last_seen` against 2-minute threshold.

## Tech Stack

- **Core runtime**: inotagent (async Python, in `inotagent/`)
- **Base image**: `python:3.12-slim` + git, gh, dbmate, uv
- **Package manager**: uv (pyproject.toml + uv.lock)
- **Database**: Postgres with pgvector (`pgvector/pgvector:pg16`)
- **Migrations**: dbmate (5 consolidated migrations in `infra/postgres/migrations/`)
- **Coding tools**: Native tools (read_file, write_file, shell)
- **Channels**: Discord (discord.py), Slack (slack-bolt), Telegram (python-telegram-bot)
- **Embedding**: Configurable in `platform.yml` (default: NVIDIA NIM `llama-nemotron-embed-1b-v2`, 1024d)
- **Containers**: Docker + docker-compose (project name: `openvaia`)
- **Default LLM**: NVIDIA NIM MiniMax-2.5 (configurable per agent via `agent.yml` or DB `agent_configs`)
- **Admin UI**: Next.js (App Router, TypeScript) + Ant Design

## Project Structure

```
inotagent/        - Custom agent runtime (async Python)
  src/inotagent/    - Source code
    llm/            - Multi-provider LLM client + embedding client + prompt gen
    tools/          - Tool registry + handlers (20 tools)
      shell.py, files.py, browser.py     - Core tools
      discord_tool.py                     - Proactive Discord messaging
      platform.py                         - Tasks + messaging + skill_create
      memory.py                           - Memory store/search (hybrid FTS + embedding)
      research.py                         - Research report store/search/get
      resources.py                        - Curated resource search/add
      email.py                            - Gmail SMTP send
      delegate.py                         - Sub-agent delegation
      setup.py                            - Wire all 20 tools into registry
    channels/       - Channel system (Discord, Slack, Telegram)
    db/             - Async Postgres (psycopg3 pool, conversations, memories, research, skills, resources, agent_configs)
    scheduler/      - Heartbeat (with recurring task reset + mission board)
    config/         - Agent, model, platform, env loaders (YAML + DB override)
    loop.py         - Core agent reasoning loop (prompt → LLM → tools → response)
    main.py         - Entry point (single-agent, multi-agent, CLI, one-shot)
    bootstrap.py    - One-time setup (register, spaces, repos, announce)
  skills/           - 81 skill files (3 global + 78 non-global, imported via make import-skills)
  tests/            - Unit tests (350 tests)
  Dockerfile        - Base image definition
  entrypoint.sh     - Container boot sequence (single + multi-agent)
  models.yml        - Model registry (providers, context windows, token limits)
  platform.yml      - Platform defaults (model, channels, embedding, prompt_gen)
Dockerfile.agents   - Multi-agent image (copies all agent dirs)
agents/             - Individual agent definitions (AGENTS.md, TOOLS.md, agent.yml)
infra/              - Postgres migrations (5 consolidated files)
scripts/            - Utility scripts (task.sh, repo.sh, import-skills.py, create-agent.sh)
docs/               - Project documentation + enhancement plans + changelogs
tests/              - Project integrity tests
ui/                 - Next.js + Ant Design admin dashboard (port 7860, dev port 3310)
resources/          - External repos (gitignored) — community agent templates for skill extraction
```

## Clean Slate Setup (from scratch)

### Prerequisites

- Docker & Docker Compose
- A Discord bot token per agent
- At least one LLM provider API key (NVIDIA NIM free tier works)

### Step 1: Bootstrap environment files

```bash
make bootstrap
```

Edit the generated files:

**`.env`** — Postgres connection:
```env
POSTGRES_HOST=postgres
POSTGRES_PORT=5445
POSTGRES_USER=inotives
POSTGRES_PASSWORD=<your-password>
POSTGRES_DB=inotives
PLATFORM_SCHEMA=openvaia
```

**`agents/ino/.env`** and **`agents/robin/.env`** — Agent credentials:
```env
NVIDIA_API_KEY=<your-nvidia-key>
DISCORD_BOT_TOKEN=<agent-specific-discord-bot-token>
GITHUB_TOKEN=<fine-grained PAT for gh CLI>
GITHUB_TOKEN_PATS=<classic PAT for git push>
```

### Step 2: Deploy

```bash
make clean-slate    # Wipe DB + rebuild + import skills (first time)
# or
make deploy-all     # Build + start (existing DB)
```

### Step 3: Verify

```bash
make ps
make logs
```

You should see:
```
Multi-agent mode: ino,robin
Agent 'ino' initialized with model 'nvidia-minimax-2.5' (20 tools, db=yes)
Agent 'robin' initialized with model 'nvidia-minimax-2.5' (20 tools, db=yes)
Starting 2 agent(s): ['ino', 'robin']
Discord connected: ino#0021
Discord connected: robin-xai#0956
```

## Boot Sequence (per container)

Defined in `inotagent/entrypoint.sh`:

1. **Git credentials** — configure `GITHUB_TOKEN_PATS` for `git push`, set `user.name` + `user.email`
2. **Ensure database** — create `POSTGRES_DB` if not exists
3. **Run migrations** — `dbmate` applies 5 consolidated migrations with schema substitution
4. **Bootstrap** — for each agent in `AGENTS`: register in `platform.agents`, seed `agent_configs`, create spaces, add members, announce boot, sync repos
5. **Start inotagent** — multi-agent: `--agents ino,robin`, single: `--agent-dir /app/agents/robin`
   - Init shared infrastructure (DB pool, embedding client)
   - Per agent: load config, load skills, create tool registry (20 tools), start heartbeat, setup channels
   - Start all agents concurrently via `asyncio.gather`

## Conventions

- DB name: `inotives` (shared across projects, isolated by schema)
- Platform schema: configurable via `PLATFORM_SCHEMA` env var (default: `platform`, ours: `openvaia`)
- Platform tables: `agents`, `spaces`, `space_members`, `messages`, `agent_status`, `config`, `tasks`, `agent_repos`, `conversations`, `memories`, `research_reports`, `skills`, `agent_skills`, `agent_configs`, `resources`
- Agent credentials: `agents/{name}/.env` (gitignored), loaded at runtime via `load_agent_env()`
- Global secrets: root `.env` (gitignored)
- Multi-agent container: `AGENTS=ino,robin` env var. `Dockerfile.agents` copies all agent dirs. Single-agent profiles: `--profile single-agent`
- Per-agent env: `agents/{name}/.env` loaded into dict at runtime — no env var collisions in multi-agent mode
- Sub-agents: `delegate` tool spawns ephemeral LLM calls using a skill as system prompt — no tools, no history
- Per-agent workspace: `/workspace/{agent_name}/` in multi-agent mode
- Shared browser: one Playwright singleton across all agents in a container
- Model selection: `agent.yml` model → DB `agent_configs` override → `platform.yml` default → first in `models.yml`
- Model fallbacks: `agent.yml` fallbacks list (overridable via DB), auto-retry on rate limit or error
- Agent configs: `agent_configs` table stores runtime-overridable settings. YAML seeds on first boot (`ON CONFLICT DO NOTHING`), UI/DB changes persist.
- Skills: 81 files in `inotagent/skills/`. `0__` = global, `1__` = non-global. Import via `make import-skills`. Token count in each file.
- Memory: hybrid search (FTS 30% + semantic 70%). Embedding model in `platform.yml`. Dynamic timestamp injected per LLM call.
- Recurring tasks: `schedule:daily@00:00`, `schedule:hourly`, `schedule:monthly@00:00` tags. Heartbeat resets done/review tasks.
- Docker project name: `openvaia`
- Docker memory: 4g multi-agent, 2g single-agent
- Schema name validation: `get_schema()` rejects non-alphanumeric values (SQL injection guard)
- Agent offline detection: `last_seen` > 2 minutes = offline in UI
- uv for package management

## Enhancement Plans

Enhancement plans live in `docs/plans/` and follow this naming and lifecycle:

- **`DRAFT__<name>.md`** — Still in discussion. Not finalized, not ready to build.
- **`ES-XXXX__<name>.md`** — Approved execution plan with a sequential code (ES-0001, ES-0002, ...). Ready to build.
- **`docs/plans/archived/`** — Completed plans. Move here once the enhancement is implemented and merged.

When starting a new enhancement, create a `DRAFT__` file first. Once the plan is reviewed and approved, rename it to the next `ES-XXXX__` code. After implementation, move it to `archived/`.

### Creating a New Execution Plan (ES)

1. Find the next ES number by checking `docs/plans/` and `docs/plans/archived/` for the highest `ES-XXXX`, increment by 1
2. Convert topic to kebab-case for filename
3. Create at: `docs/plans/ES-XXXX__<topic>.md`

Template:
```markdown
# ES-XXXX — <Title>

## Problem / Pain Points
## Suggested Solution
## Implementation Steps
- [ ] Step 1
- [ ] Step 2

## Status: PENDING
```

### Completed
- `ES-0001` — Prompt Generator Functions
- `ES-0002` — Daily Reviews & Agent Self-Improvement Skills
- `ES-0003` — Agent Email Send
- `ES-0004` — Curated Resources Registry
- `ES-0005` — Skill Templates from Community (81 skills)
- `ES-0006` — Recurring Tasks Replace Cron
- `ES-0007` — Multi-Agent Container & Sub-Agents

### In Discussion
- `DRAFT__openvaia_prod_deployment` — Production deployment guide
- `DRAFT__parallel_task_execution` — Concurrent LLM chains

## File Size Check (keep under 800 lines)

```bash
find . -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.sh" \) \
  ! -path "*/node_modules/*" ! -path "*/.next/*" ! -path "*/.venv/*" ! -path "*/__pycache__/*" \
  -exec wc -l {} + | awk '$1 >= 800 && !/total$/' | sort -rn
```

## Branch Changelogs

Each feature branch keeps a changelog in `docs/changelogs/`:

- **Format**: `CHG_<YYYYMMDD>_<branch_name>.md`
- **Create** when a new branch starts
- **Update** as changes are made
- **Keep** after merge as historical record

## Commands

```
# Deployment
make deploy-all              - Build + start with local Postgres (multi-agent default)
make deploy                  - Build + start agents (no Postgres)
make db                      - Start only Postgres
make clean-slate             - Wipe DB + rebuild + import skills

# Operations
make start                   - Start containers
make stop AGENT=ino          - Stop specific agent
make restart AGENT=ino       - Restart specific agent
make down                    - Tear down everything
make wipe-db                 - Wipe DB schema only

# Monitoring
make ps                      - Show running services
make logs                    - Last 40 lines of logs
make logs-follow             - Live log tail
make shell AGENT=ino         - Shell into container

# Skills
make import-skills           - Import skills from inotagent/skills/ (skip existing)
make reset-skill NAME=x      - Reset one skill to file version
make reimport-skills         - Force re-import all skills
make seed-tasks              - Seed recurring tasks for proactive agent behavior

# Admin UI
make ui                      - Build + start Docker UI (port 7860)
make ui-install              - npm install for local dev
make ui-dev                  - Start local dev server (port 3310)
make ui-dev-restart          - Kill + restart dev server

# Tasks
make task-list [AGENT= STATUS=]
make task-get KEY=INO-001
make task-create TITLE="..." BY=boss TO=robin TAGS=schedule:daily@00:00
make task-update KEY=INO-001 STATUS=done
make task-summary [AGENT=]
make task-board

# Repos
make repo-list [AGENT=]
make repo-add URL=... NAME=... TO=robin BY=ino
make repo-remove URL=... AGENT=robin

# Testing
make test                    - Project integrity tests
make inotagent-test          - 350 unit tests
make bootstrap               - Generate .env from templates
make create-agent NAME=kai   - Create new agent from template
```
