# Plan: Replace Gradio Admin UI with AdminJS

## Overview

Replace the current Python/Gradio admin UI (`ui/`) with a Node.js-based [AdminJS](https://docs.adminjs.co) panel. AdminJS auto-generates CRUD interfaces from Postgres tables and supports custom React components for specialized views like the kanban board.

## Why

- Auto-generated CRUD for all platform tables — less code to maintain
- Node-based — aligns with OpenClaw runtime (Node)
- Built-in filtering, sorting, pagination, search
- Customizable with React components
- Better suited as an admin panel than Gradio (which is designed for ML demos)

## Scope

### What changes
- `ui/` folder — full rewrite from Python/Gradio to Node/AdminJS
- `ui/Dockerfile` — switch from Python slim to Node image
- `docker-compose.yml` — update UI service configuration
- `tests/test_ui.py` — rewrite or replace UI tests

### What stays the same
- All Postgres tables and schema (AdminJS connects directly)
- All agent containers, scripts, CLI tools
- All core runtime code
- Docker network and Postgres service

---

## Phase 1: Project Setup

### Tasks
1. Initialize Node.js project in `ui/` with `package.json`
   - Dependencies: `adminjs`, `@adminjs/express`, `@adminjs/sql` (Postgres adapter), `express`, `express-session`
2. Create `ui/Dockerfile` based on `node:20-slim`
   - Install dependencies, copy source, expose port 7860
3. Create `ui/app.js` — AdminJS entry point
   - Connect to Postgres using env vars (`POSTGRES_HOST`, `POSTGRES_USER`, etc.)
   - Use `PLATFORM_SCHEMA` env var for schema name
   - Listen on port 7860
4. Update `docker-compose.yml` UI service
   - Update build context and Dockerfile reference
   - Keep same env vars and network config
5. Verify basic AdminJS panel loads at `http://localhost:7860`

### Acceptance
- AdminJS panel is accessible in the browser
- Connected to Postgres with correct schema

---

## Phase 2: Auto-Generated CRUD Resources

### Tasks
1. Register all platform tables as AdminJS resources:
   - `agents` — agent registry
   - `agent_status` — health check history
   - `spaces` — communication spaces
   - `space_members` — space membership
   - `messages` — message history
   - `config` — runtime config key/value
   - `tasks` — task management
   - `agent_repos` — repo assignments
2. Configure display options per resource:
   - `tasks`: list columns = key, title, status, priority, assigned_to, created_by, repo (via relation)
   - `agents`: list columns = name, status, last_seen
   - `messages`: list columns = from_agent, body (truncated), space_id, created_at
   - `config`: list columns = key, value, description, updated_at
   - `agent_repos`: list columns = agent_name, name, repo_url, assigned_by
3. Configure relationships:
   - `tasks.repo_id` → `agent_repos.id` (show repo name)
   - `tasks.parent_task_id` → `tasks.id` (show parent task key)
   - `messages.space_id` → `spaces.id` (show space name)
4. Add basic validation rules:
   - `tasks`: title and created_by required
   - `config`: key and value required
   - `agent_repos`: agent_name, repo_url, name, assigned_by required

### Acceptance
- All 8 tables have working list/show/create/edit/delete views
- Relationships display correctly (e.g., task shows repo name)
- Filtering and sorting work on all list views

---

## Phase 3: Custom Dashboard

### Tasks
1. Create custom AdminJS dashboard component (`ui/components/Dashboard.jsx`)
2. Dashboard should display:
   - Agent status summary (online/offline count, list with last_seen)
   - Task summary (counts by status: todo, in_progress, done, blocked)
   - Recent messages (last 10 messages across all spaces)
3. Dashboard queries:
   - `SELECT name, status, last_seen FROM agents ORDER BY last_seen DESC`
   - `SELECT status, COUNT(*) FROM tasks GROUP BY status`
   - `SELECT from_agent, body, created_at FROM messages ORDER BY created_at DESC LIMIT 10`
4. Register as the default dashboard in AdminJS config

### Acceptance
- Dashboard loads as the landing page
- Shows live agent status, task counts, and recent messages
- Auto-refreshes or has a refresh button

---

## Phase 4: Kanban Board

### Tasks
1. Create custom React component (`ui/components/KanbanBoard.jsx`)
2. Kanban columns: `backlog`, `todo`, `in_progress`, `review`, `done`, `blocked`
3. Each card shows: task key, title, priority (color-coded), assigned_to, repo name
4. Click on card → navigate to task detail/edit page
5. Optional: drag-and-drop to change task status (PATCH via AdminJS API)
6. Add filter controls: by agent, by priority, by repo
7. Register as a custom page in AdminJS navigation (e.g., "Kanban Board" menu item)

### Acceptance
- Kanban board shows all tasks in correct columns
- Cards are color-coded by priority
- Click navigates to task detail
- Filters work correctly

---

## Phase 5: Custom Actions

### Tasks
1. **Send Message** action on the Messages resource
   - Form: select space, from_agent, body text
   - Inserts into messages table
2. **Quick Status Update** bulk action on Tasks resource
   - Select multiple tasks → set status in one click
3. **Register Agent** action on Agents resource
   - Form: agent name → inserts into agents table with status 'offline'

### Acceptance
- Send message works from the admin panel
- Bulk task status update works
- Agent registration works

---

## Phase 6: Authentication & Polish

### Tasks
1. Add basic auth using `express-session` + env vars (`UI_USERNAME`, `UI_PASSWORD`)
   - Match current Gradio auth behavior
2. Customize AdminJS branding:
   - App name: "inotives_aibots"
   - Logo (optional)
3. Update tests:
   - Test that AdminJS app builds and starts
   - Test that all resources are registered
   - Test Dockerfile structure
4. Update documentation:
   - CLAUDE.md, README.md, docs/project_summary.md

### Acceptance
- Auth works when env vars are set, skipped when empty
- Tests pass
- Documentation is up to date

---

## File Structure (Target)

```
ui/
├── package.json
├── Dockerfile
├── app.js                    # AdminJS entry point + Express server
├── resources/                # Resource configurations per table
│   ├── agents.js
│   ├── tasks.js
│   ├── messages.js
│   ├── config.js
│   ├── agent_repos.js
│   └── ...
└── components/               # Custom React components
    ├── Dashboard.jsx
    └── KanbanBoard.jsx
```

## Dependencies

```json
{
  "adminjs": "^7.x",
  "@adminjs/express": "^6.x",
  "@adminjs/sql": "^2.x",
  "express": "^4.x",
  "express-session": "^1.x",
  "pg": "^8.x"
}
```

## Notes

- Keep port 7860 for backward compatibility
- Use same env vars as current Gradio UI (POSTGRES_HOST, POSTGRES_USER, etc.)
- `PLATFORM_SCHEMA` env var determines which schema to use
- The current `tests/test_ui.py` will need full rewrite — Gradio-specific tests won't apply
- Old `ui/` Python files can be deleted once AdminJS is verified working
