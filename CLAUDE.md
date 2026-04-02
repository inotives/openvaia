# OpenVAIA — Claude Agent Workflow Guide

For project overview, see `docs/project_summary.md`. For technical specs, see `docs/project_specs.md`.

## Quick Reference

- **103 skill files** (5 global + 98 non-global) in `inotagent/skills/`
- **22 tools** in `inotagent/src/inotagent/tools/`
- **7 DB migrations** in `infra/postgres/migrations/`
- **Runtime**: inotagent (async Python), Docker, Postgres + pgvector
- **UI**: Next.js + Ant Design (port 7860), Gamified Office (`/office`)
- **Package managers**: uv (Python), npm (UI)

## Conventions

- DB: `inotives` (shared across projects, isolated by `PLATFORM_SCHEMA` env var, ours: `openvaia`)
- Agent credentials: `agents/{name}/.env` (gitignored)
- Global secrets: root `.env` (gitignored)
- Multi-agent: `AGENTS=ino,robin` env var
- Per-agent workspace: `/workspace/{agent_name}/`
- Skills: `0__` prefix = global (all agents), `1__` prefix = non-global (equip via UI)
- Docker project name: `openvaia`
- uv for Python package management

## Development Workflow

This is the standard workflow for all feature development in this project:

### 1. Plan (ES-XXXX)
- Create an Enhancement Plan (`docs/plans/ES-XXXX__<topic>.md`)
- Define: problem, solution, implementation phases, guardrails
- Discuss and refine until approved
- Commit the plan to main

### 2. Branch
- Create feature branch: `git checkout -b feature/<topic>`
- Create changelog: `docs/changelogs/CHG_<YYYYMMDD>_<branch>.md`

### 3. Implement (per phase)
For each phase in the ES plan:
1. **Implement** the phase (code, skills, migrations, API endpoints)
2. **Test** — verify it works (run locally, check logs, validate DB)
3. **Update changelog** with what was done
4. **Commit** the phase with descriptive message

Repeat until all phases are complete.

### 4. Review
- Security audit — check for leaked secrets, SQL injection, XSS
- Update docs — CLAUDE.md, project_summary.md, project_specs.md, README.md
- Verify all counts are accurate (skills, tools, migrations)
- Final commit with doc updates

### 5. Push & PR
- Push branch: `git push -u origin feature/<topic>`
- Create PR with summary + test plan
- Human reviews and merges

### 6. Cleanup
- `git checkout main && git pull origin main`
- Move completed ES plan to `docs/plans/archived/` (if fully done)
- Start next feature

### Hotfixes
For urgent fixes outside of a plan:
- Commit directly to main with `fix:` prefix
- Push immediately: `git push origin main`
- Rebuild: `make deploy-all`

## Enhancement Plans

Plans live in `docs/plans/` with this lifecycle:

- **`DRAFT__<name>.md`** — In discussion, not ready to build
- **`ES-XXXX__<name>.md`** — Approved, sequential code (ES-0001, ES-0002, ...). Ready to build.
- **`docs/plans/archived/`** — Completed. Move here after merge.

### Creating a New ES

1. Find next ES number: check `docs/plans/` and `docs/plans/archived/`
2. Create: `docs/plans/ES-XXXX__<topic-kebab-case>.md`

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

### Completed Plans
- ES-0001 through ES-0007: v1 foundation (runtime, tools, channels, skills, recurring tasks, multi-agent)
- ES-0008: Gamified pixel office UI
- ES-0009: Proactive agent behavior (idle detection, recurring tasks, human priority interrupt)
- ES-0010: Self-evolving skills (metrics, versioning, proposals)
- ES-0013: Spec-driven development skills (proposal, spec, design, verification)

### In Progress / Draft
- ES-0012: Robin trading toolkit
- ES-0014: Dynamic skill equipping (skill chains)
- DRAFT: Production deployment, parallel execution

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
make clean-slate             - Wipe DB + rebuild + import skills + seed tasks

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
make seed-chains             - Seed skill chains for dynamic skill equipping

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

# Local Development (without Docker)
make local-setup             - First time: install deps + migrate + seed everything
make local-run AGENT=ino     - Run single agent locally
make local-run-multi         - Run multi-agent locally (AGENTS=ino,robin)
make local-stop              - Stop locally running agents
make local-install           - Install Python deps via uv
make local-migrate           - Run DB migrations locally

# Testing
make test                    - Project integrity tests
make inotagent-test          - 350 unit tests
make bootstrap               - Generate .env from templates
make create-agent NAME=kai   - Create new agent from template
```
