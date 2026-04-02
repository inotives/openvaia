# OpenVAIA — Project Summary

Dockerized multi-agent AI platform powered by **inotagent** — a custom async Python runtime. For technical specs, see `project_specs.md`.

## Core Concept

**Container = Company. Agent = Worker.**

- A **container** is the company — it provides infrastructure (shell, files, browser, channels, memory, LLM). Multiple agents share one container or run 1:1.
- An **agent** is a worker — it has a name, personality, credentials, and its own way of working.
- Agents can **delegate** work to other agents via the `delegate` tool, enabling sub-agent workflows.
- All agents share the same base image and toolset. Each picks their own brain (LLM model) from a central registry.

## Design Philosophy

**inotagent-first, runtime-pluggable** — inotagent is the default runtime, but agents are separated from the engine:

- `inotagent/` is the **runtime engine** — LLM client, tools, channels, persistence, scheduling.
- `agents/` are the **deployable individuals** — identity (AGENTS.md), tool rules (TOOLS.md), model preferences (agent.yml), credentials (.env).

Agents are consumers of the runtime, not part of it. Agent identity files carry over to any compatible runtime.

**DB-driven skills** — Skills are markdown modules stored in Postgres, injected into the agent's system prompt at startup and refreshed every heartbeat (60s). Skills can be edited via Admin UI without redeploy.

**Hybrid memory** — Agent memories are searched via Postgres FTS (30%) + pgvector embeddings (70%). Keywords catch exact matches, embeddings catch meaning.

**Self-evolving skills** — Agents propose skill improvements (FIX/DERIVED/CAPTURED) via `skill_propose` tool. Human reviews and approves. Full version history with lineage tracking.

## Communication

- **Agent-to-agent**: Postgres spaces (public, tasks, room, direct)
- **Agent-to-human**: Discord, Slack, Telegram, Admin UI web chat
- **Proactive**: Agents autonomously work when idle — research, monitoring, resource discovery

## Task Workflow

**Human → Agent → Human**:
1. Boss creates task (Discord or `make task-create`)
2. Agent heartbeat detects pending task, picks it up
3. Agent works on it (coding, research, analysis)
4. Agent sets status to `review` with results
5. Boss reviews and approves

**Agent → Agent** (delegation):
1. Agent A creates task assigned to Agent B
2. Agent B picks up, completes, sets to `review`
3. Agent A reviews and accepts

**Mission Board** (self-service):
1. Boss creates unassigned backlog task with tags
2. Agents with matching `mission_tags` auto-detect via heartbeat
3. Agent self-assigns and starts working

**Proactive behavior**: Agents create and execute autonomous tasks during idle time (market monitoring, resource discovery, operations checks).

## Agents

- **ino** (Global Financial Researcher) — markets, APIs, data sources, crypto, equities, macro. Delivers structured reports.
- **robin** (Trading Operations Engineer) — trading systems, data pipelines, strategy implementation, infrastructure.

## What's Built

### v1 — Core Runtime (ES-0001 through ES-0007)
- Custom async Python runtime (inotagent)
- Multi-provider LLM client (Anthropic, OpenAI-compatible, NVIDIA NIM, Groq, Google)
- 22-tool system (shell, files, browser, Discord, tasks, messaging, memory, research, resources, email, delegation, skill creation, skill proposals, skill equip)
- Multi-channel: Discord, Slack, Telegram
- Async Postgres persistence (conversations, memory with hybrid FTS + embedding search, research reports)
- Heartbeat with recurring task scheduling
- Mission board (unassigned backlog + agent self-selection)
- Sub-agent delegation via `delegate` tool
- DB-driven skills system (103 skill files from 5 sources)
- Admin dashboard (Next.js + Ant Design)

### v1.3 — Gamified Office UI (ES-0008)
- 2D pixel art office built with PixiJS v8
- Agents move between rooms based on current activity
- Interactive doors, elevator buttons, LED indicators
- Agent panel: Chat, Skills (equip/unequip), Research, Memory

### v1.4 — Proactive Agents + Self-Evolving Skills (ES-0009, ES-0010, ES-0013)
- Proactive agent behavior — recurring tasks, idle behavior, human priority interrupt
- Self-evolving skills — metrics, versioning, proposals (FIX/DERIVED/CAPTURED)
- Spec-driven development skills — proposal (PROP:), spec (SPEC:), design (DESIGN:), verification (VERIFY:)
- Global development workflow orchestration skill
- 103 skills total (5 global + 98 non-global)

### ES-0014 — Dynamic Skill Equipping
- [x] Skill chains DB (`skill_chains` table) with 12 default chains seeded
- [x] Task-aware skill loading — tags auto-match to chains, load phase-specific skills
- [x] Chain state tracking on tasks (`chain_state` JSONB) with auto-advancement
- [x] Human approval gates — chain steps can pause task for review
- [x] Skill usage recorded in conversation metadata (skills, chain, phase)
- [x] `skill_equip` tool (#22) — load any skill mid-conversation on-demand
- [x] Token budget enforcement (9000 max), deduplication, static fallback

## What's Next
- **ES-0012** — Robin trading toolkit (agent-first CLI tools for autonomous crypto trading)
- Production deployment (internet-facing hosting)
- Parallel execution (concurrent tool calls)

## References

- Technical specs: `docs/project_specs.md`
- Enhancement plans: `docs/plans/`
- Changelogs: `docs/changelogs/`
