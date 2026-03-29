# Phase 4: Research Reports Viewer + Real-time Updates

## Goal

Two new capabilities:
1. Browse and search research reports stored by agents, with full markdown rendering
2. SSE-based real-time updates for dashboard, tasks, and messages (no manual refresh)

---

## Research Reports — `/reports`

### Report List Page — `/reports`

Top bar with:
- Search input (full-text search)
- Agent filter (`Select`)
- Tag filter (`Select` with multiple, populated from distinct tags)
- Results count

Below: report cards in a list/grid. Each card shows:
- Title
- Agent name + date
- Summary (first 200 chars)
- Tags as Ant Design `Tag` components
- Click → navigate to `/reports/[id]`

### Single Report Page — `/reports/[id]`

- Back button → `/reports`
- Header: title, agent, date, linked task key
- Tags
- Full body rendered as markdown (`MarkdownRenderer` component)

### MarkdownRenderer Component

Shared component using:
- `react-markdown` for markdown parsing
- `remark-gfm` for tables, strikethrough, task lists
- `rehype-highlight` for code syntax highlighting

Styled to work with Ant Design's typography.

```bash
npm install react-markdown remark-gfm rehype-highlight
```

### API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `GET /api/reports` | GET | Search/list reports |
| `GET /api/reports/[id]` | GET | Single report with full body |

**`GET /api/reports`** query params: `?search=`, `?agent=`, `?tags=` (comma-separated), `?limit=`, `?offset=`

```sql
SELECT id, agent_name, task_key, title, summary, tags, created_at
FROM {schema}.research_reports
WHERE ($1::text IS NULL OR to_tsvector('english', title || ' ' || summary || ' ' || body) @@ plainto_tsquery('english', $1))
  AND ($2::text IS NULL OR agent_name = $2)
  AND ($3::text[] IS NULL OR tags @> $3)
ORDER BY created_at DESC
LIMIT $4 OFFSET $5
```

Uses existing GIN indexes: `idx_research_reports_fts` and `idx_research_reports_tags`.

**`GET /api/reports/[id]`**:

```sql
SELECT id, agent_name, task_key, title, summary, body, tags, created_at
FROM {schema}.research_reports
WHERE id = $1
```

---

## Real-time Updates (SSE)

### Server — `src/app/api/sse/route.ts`

Next.js streaming response using `ReadableStream`:

```typescript
export async function GET() {
  const stream = new ReadableStream({
    async start(controller) {
      let lastCheck = new Date();
      const interval = setInterval(async () => {
        const events = await checkForChanges(lastCheck);
        for (const event of events) {
          controller.enqueue(`event: ${event.type}\ndata: ${JSON.stringify(event.data)}\n\n`);
        }
        lastCheck = new Date();
      }, 5000);

      // Cleanup on disconnect
      controller.close = () => clearInterval(interval);
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
```

### Change Detection — `src/lib/sse.ts`

Polls DB every 5 seconds for:

```sql
-- New/updated tasks since last check
SELECT key, status, updated_at FROM {schema}.tasks WHERE updated_at > $1

-- Agent status changes
SELECT name, status, last_seen FROM {schema}.agents WHERE last_seen > $1

-- New messages
SELECT COUNT(*) as count FROM {schema}.messages WHERE created_at > $1
```

### Event Types

| Event | Payload | Consumed By |
|-------|---------|-------------|
| `task-update` | `{key, status, updated_at}` | Tasks page (refresh board) |
| `agent-status` | `{name, status, last_seen}` | Dashboard (refresh agent table) |
| `new-message` | `{count}` | Dashboard + Messages (refresh) |

### Client Hook — `src/hooks/useSSE.ts`

```typescript
export function useSSE(onEvent: (type: string, data: any) => void) {
  useEffect(() => {
    const source = new EventSource("/api/sse");
    source.addEventListener("task-update", (e) => onEvent("task-update", JSON.parse(e.data)));
    source.addEventListener("agent-status", (e) => onEvent("agent-status", JSON.parse(e.data)));
    source.addEventListener("new-message", (e) => onEvent("new-message", JSON.parse(e.data)));
    return () => source.close();
  }, [onEvent]);
}
```

### Integration Points

- **Dashboard**: Subscribe to all events. Show subtle notification dot or auto-refresh tables.
- **Tasks/KanbanBoard**: Subscribe to `task-update`. Flash updated cards or auto-refresh.
- **Messages**: Subscribe to `new-message`. If viewing affected space, show "new messages" banner.

---

## Dependencies Added

```bash
npm install react-markdown remark-gfm rehype-highlight
```

## Verification

1. `/reports` — search returns results, filters work, cards render
2. `/reports/[id]` — full markdown body renders with code highlighting
3. Open dashboard in two tabs → update a task in one → other tab updates within 5s
4. SSE connection visible in browser DevTools Network tab
