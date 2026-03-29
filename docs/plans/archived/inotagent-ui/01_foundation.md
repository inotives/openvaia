# Phase 1: Foundation + Dashboard

## Goal

A deployable Next.js app on port 7860 in Docker, with DB connectivity, basic auth, sidebar navigation, and a working Dashboard page.

## Scaffold

Initialize the Next.js project in `ui/`:

```bash
npx create-next-app@latest ui --typescript --app --src-dir --no-tailwind --no-eslint
```

Install dependencies:

```bash
cd ui
npm install antd @ant-design/nextjs-registry @ant-design/icons postgres
```

### next.config.ts

```typescript
const nextConfig = {
  output: "standalone",  // Minimal Docker image
  reactStrictMode: true,
};
export default nextConfig;
```

## DB Layer — `src/lib/db.ts`

```typescript
import postgres from "postgres";

const SCHEMA = process.env.PLATFORM_SCHEMA || "platform";

const sql = postgres({
  host: process.env.POSTGRES_HOST || "localhost",
  port: Number(process.env.POSTGRES_PORT) || 5432,
  user: process.env.POSTGRES_USER,
  password: process.env.POSTGRES_PASSWORD,
  database: process.env.POSTGRES_DB,
  max: 5,
});

export { sql, SCHEMA };
```

Schema is interpolated as an identifier in queries:
```typescript
const agents = await sql`SELECT * FROM ${sql(SCHEMA)}.agents`;
```

## Auth — `src/middleware.ts`

Check `UI_USERNAME` + `UI_PASSWORD` env vars. If both set, enforce HTTP Basic Auth on all routes except `/api/*` (API routes handle their own auth if needed).

```typescript
import { NextRequest, NextResponse } from "next/server";

export function middleware(req: NextRequest) {
  const user = process.env.UI_USERNAME;
  const pass = process.env.UI_PASSWORD;
  if (!user || !pass) return NextResponse.next();

  const auth = req.headers.get("authorization");
  if (!auth) return unauthorized();

  const [scheme, encoded] = auth.split(" ");
  if (scheme !== "Basic") return unauthorized();

  const [u, p] = Buffer.from(encoded, "base64").toString().split(":");
  if (u === user && p === pass) return NextResponse.next();
  return unauthorized();
}

function unauthorized() {
  return new NextResponse("Unauthorized", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="inotagent"' },
  });
}

export const config = { matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"] };
```

## Layout — `src/app/layout.tsx`

Root layout with Ant Design `ConfigProvider` + `AntdRegistry` for SSR. Sidebar uses `Layout` + `Sider` + `Menu` with navigation items:

- Dashboard (`/dashboard`)
- Tasks (`/tasks`)
- Messages (`/messages`)
- Agents (`/agents`)
- Config (`/config`)

Additional items added in later phases (Reports, Chat, Management).

## Component — `src/components/AppLayout.tsx`

Ant Design `Layout` with collapsible `Sider`:
- Logo/title at top
- `Menu` with `usePathname()` for active highlighting
- `Content` area renders `{children}`

## Dashboard Page — `src/app/dashboard/page.tsx`

Three sections, each fetching from an API route:

1. **Agent Status** — Ant Design `Table` showing: name, status, healthy (boolean tag), uptime, last seen
2. **Task Summary** — Ant Design `Table` showing: agent, backlog, todo, in_progress, review, done, blocked counts
3. **Recent Messages** — Ant Design `Table` showing: from, space, message (truncated), timestamp

Each section has a refresh button. Data fetched client-side via `fetch()`.

## API Routes

### `GET /api/dashboard/agents`

```sql
SELECT a.name, a.status, a.last_seen,
       s.openclaw_healthy, s.details, s.checked_at
FROM {schema}.agents a
LEFT JOIN LATERAL (
    SELECT openclaw_healthy, details, checked_at
    FROM {schema}.agent_status
    WHERE agent_name = a.name
    ORDER BY checked_at DESC LIMIT 1
) s ON true
ORDER BY a.name
```

### `GET /api/dashboard/tasks`

```sql
SELECT
  COALESCE(assigned_to, created_by) AS agent,
  status, COUNT(*) AS count
FROM {schema}.tasks
GROUP BY agent, status
ORDER BY agent, status
```

Pivot in TypeScript to produce rows: `{agent, backlog, todo, in_progress, review, done, blocked}`.

### `GET /api/dashboard/messages`

```sql
SELECT m.from_agent, s.name AS space_name, m.body, m.created_at
FROM {schema}.messages m
JOIN {schema}.spaces s ON s.id = m.space_id
ORDER BY m.created_at DESC
LIMIT 20
```

## Constants — `src/lib/constants.ts`

Port from current `ui/tabs/tasks.py`:

```typescript
export const STATUSES = ["backlog", "todo", "in_progress", "review", "done", "blocked"] as const;
export const PRIORITIES = ["critical", "high", "medium", "low"] as const;

export const STATUS_COLORS: Record<string, string> = {
  backlog: "#94a3b8", todo: "#3b82f6", in_progress: "#f59e0b",
  review: "#8b5cf6", done: "#22c55e", blocked: "#ef4444",
};

export const PRIORITY_COLORS: Record<string, string> = {
  critical: "#dc2626", high: "#ea580c", medium: "#2563eb", low: "#6b7280",
};
```

## Dockerfile

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 7860
ENV PORT=7860
CMD ["node", "server.js"]
```

## Docker Compose

Update `ui` service — same ports, env, network, memory limit. Change `dockerfile` reference stays `ui/Dockerfile`.

## Root Page — `src/app/page.tsx`

Redirect to `/dashboard`:
```typescript
import { redirect } from "next/navigation";
export default function Home() { redirect("/dashboard"); }
```

## Stub Pages

Create `page.tsx` for `/tasks`, `/messages`, `/agents`, `/config` with placeholder content:
```typescript
export default function TasksPage() {
  return <div>Tasks — Coming in Phase 2</div>;
}
```

## Verification

1. `docker compose up -d --build ui` — container starts
2. `http://localhost:7860` → redirects to `/dashboard`
3. Dashboard tables show data from Postgres
4. Sidebar navigation works (stubs load)
5. Basic auth works if env vars set
