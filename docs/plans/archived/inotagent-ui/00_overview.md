# inotagent UI — Overview

## Why

The current Gradio dashboard is functional but limited: no real-time updates, no markdown rendering, clunky kanban, no chat interface. Replace it with a modern React UI that can grow with the platform.

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Framework | Next.js (App Router) | API routes built-in, SSR, TypeScript, file-based routing |
| Components | Ant Design | Enterprise-grade tables, forms, drawers, layout. Rich out of the box |
| DB client | postgres.js (porsager/postgres) | Tagged template literals, no ORM overhead, safe parameterization |
| Styling | Ant Design built-in + CSS modules where needed | Consistent design system |
| Real-time | Server-Sent Events (SSE) | Simpler than WebSocket, auto-reconnect, proxy-friendly |
| Markdown | react-markdown + remark-gfm + rehype-highlight | For research report rendering |
| Docker | node:20-alpine, standalone output | Small image, fits 512MB memory limit |

## Architecture

```
Browser
  |
  v
Next.js (port 7860)
  ├── Pages (React + Ant Design)
  ├── API Routes (/api/*)
  │     └── postgres.js → Postgres
  └── SSE endpoint (/api/sse)
        └── polls DB every 5s, pushes events
```

- **No separate backend** — Next.js API routes handle all DB queries
- **Schema-aware** — `PLATFORM_SCHEMA` env var injected into SQL (same as current Python code)
- **Auth** — Next.js middleware checks `UI_USERNAME`/`UI_PASSWORD` for HTTP Basic Auth

## Pages

| Page | URL | Status |
|------|-----|--------|
| Dashboard | `/dashboard` | Phase 1 |
| Tasks (Kanban) | `/tasks` | Phase 2 |
| Messages | `/messages` | Phase 3 |
| Agents | `/agents` | Phase 3 |
| Config | `/config` | Phase 3 |
| Research Reports | `/reports`, `/reports/[id]` | Phase 4 |
| Agent Chat | `/chat` | Phase 5 |
| Agent Management | `/management` | Phase 5 |

## Phase Summary

| Phase | Scope | Key Deliverables |
|-------|-------|------------------|
| 1 | Foundation + Dashboard | Next.js in Docker, DB layer, sidebar nav, dashboard page |
| 2 | Task Board | Kanban (6 cols), task detail drawer, create/update |
| 3 | Messages + Agents + Config | Full Gradio parity |
| 4 | Reports + Real-time | Research report viewer, SSE live updates |
| 5 | Chat + Management | Agent chat UI, agent lifecycle management |
| 6 | Tests + Polish | Rewrite tests, loading states, dark mode |

Each phase is independently deployable.

## Docker Constraints (preserved)

- Port: `7860` (configurable via `UI_PORT`)
- Env: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `PLATFORM_SCHEMA`
- Network: `platform`
- Memory: 512MB
- Auth: optional `UI_USERNAME`/`UI_PASSWORD`
