# Phase 6: Tests + Navigation + Polish

## Goal

Rewrite `tests/test_ui.py` for the new Next.js stack. Update sidebar navigation to include all pages. Polish the entire UI with loading states, error handling, and dark mode.

---

## Test Rewrite — `tests/test_ui.py`

Keep as a Python pytest file (project runs `make test` with pytest). Tests validate structure and Docker integration — no need for a Node.js test runner.

### Test Classes

**`TestUIFileStructure`** — Validate key files exist:
- `ui/package.json`
- `ui/tsconfig.json`
- `ui/next.config.ts`
- `ui/Dockerfile`
- `ui/src/app/layout.tsx`
- `ui/src/app/dashboard/page.tsx`
- `ui/src/app/tasks/page.tsx`
- `ui/src/app/messages/page.tsx`
- `ui/src/app/agents/page.tsx`
- `ui/src/app/config/page.tsx`
- `ui/src/app/reports/page.tsx`
- `ui/src/app/chat/page.tsx`
- `ui/src/app/management/page.tsx`
- `ui/src/lib/db.ts`
- `ui/src/middleware.ts`

**`TestUIDockerCompose`** — Same as current:
- `ui` service exists in docker-compose.yml
- References `ui/Dockerfile`
- Port 7860 exposed
- On `platform` network
- Memory limit 512m

**`TestUIMakefile`** — Targets exist:
- `ui:`
- `ui-logs:`

**`TestUIDockerfile`** — Validate Dockerfile contents:
- Uses `node:20-alpine`
- Exposes 7860
- Runs `node server.js`
- Multi-stage build (builder + runner)

**`TestUIPackageJson`** — Parse `package.json`, verify dependencies:
- `next`
- `react`
- `antd`
- `@ant-design/nextjs-registry`
- `postgres`

**`TestAPIRoutes`** — Verify API route files exist:
- `ui/src/app/api/dashboard/agents/route.ts`
- `ui/src/app/api/dashboard/tasks/route.ts`
- `ui/src/app/api/tasks/route.ts`
- `ui/src/app/api/messages/route.ts`
- `ui/src/app/api/spaces/route.ts`
- `ui/src/app/api/agents/route.ts`
- `ui/src/app/api/config/route.ts`
- `ui/src/app/api/reports/route.ts`
- `ui/src/app/api/sse/route.ts`
- `ui/src/app/api/chat/route.ts`

---

## Navigation Update — `AppLayout.tsx`

Update sidebar menu to include all 8 pages:

| Icon | Label | Path | Phase |
|------|-------|------|-------|
| DashboardOutlined | Dashboard | `/dashboard` | 1 |
| ProjectOutlined | Tasks | `/tasks` | 2 |
| MessageOutlined | Messages | `/messages` | 3 |
| RobotOutlined | Agents | `/agents` | 3 |
| SettingOutlined | Config | `/config` | 3 |
| FileTextOutlined | Reports | `/reports` | 4 |
| CommentOutlined | Chat | `/chat` | 5 |
| ToolOutlined | Management | `/management` | 5 |

Group into sections:
- **Overview**: Dashboard
- **Operations**: Tasks, Messages
- **System**: Agents, Config, Management
- **Research**: Reports
- **Communication**: Chat

---

## Polish Items

### Loading States
- Ant Design `Skeleton` for tables during initial load
- `Spin` indicator for button actions (create, update, delete)
- Skeleton cards for kanban board columns

### Error Handling
- Ant Design `Result` component for error states (500, connection failed)
- `message.error()` notifications for failed API calls
- Graceful fallback when Postgres is unavailable (show "DB unavailable" banner)
- Error boundary component wrapping each page

### Empty States
- Ant Design `Empty` component when tables/lists have no data
- Contextual messages: "No tasks yet", "No reports found", etc.

### Responsive Layout
- Sidebar collapses to icons on small screens (Ant Design `Sider` breakpoint)
- Kanban board horizontal scroll on narrow viewports
- Tables switch to card layout on mobile (optional)

### Dark Mode
- Ant Design `ConfigProvider` with `theme.algorithm`
- Toggle button in sidebar footer
- Persist preference in `localStorage`
- Default: follow system preference via `prefers-color-scheme`

### Page Titles
- `metadata` export per page for browser tab titles
- Format: `Page Name | inotagent`

### Favicon
- Simple robot/gear icon as favicon

---

## Verification

1. `make test` — all Python tests pass (integrity + UI structure)
2. All 8 pages load without errors
3. Loading skeletons visible during data fetch
4. Error states render when API fails
5. Dark mode toggle works
6. Sidebar collapses on narrow viewport
7. Browser tab titles are correct per page
