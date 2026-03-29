# Phase 2: Task Board (Kanban + CRUD)

## Goal

Full kanban board with 6 status columns, task detail drawer, create task modal, quick status update, and agent filter. This is the most complex page.

## Components

### `KanbanBoard.tsx`

Client component (`'use client'`). Top bar with:
- Agent filter (`Select` with "All" + agent names)
- Create task button → opens `CreateTaskModal`
- Refresh button

Fetches tasks from `/api/tasks?agent=X`, groups by status into 6 columns. Each column rendered by `KanbanColumn`.

### `KanbanColumn.tsx`

Single column with:
- Header: status label + count badge, colored by `STATUS_COLORS`
- Scrollable card list
- Empty state when no tasks

### `TaskCard.tsx`

Ant Design `Card` (compact). Displays:
- Task key (subdued, e.g. `INO-001`)
- Title (bold, truncated to 2 lines)
- Priority tag (colored by `PRIORITY_COLORS`)
- Assigned agent name
- Parent task indicator (if has parent)

Click opens `TaskDetailDrawer`.

### `TaskDetailDrawer.tsx`

Ant Design `Drawer` (right side, 480px). Shows:
- Header: task key + status tag
- Metadata grid: priority, assigned_to, created_by, created_at, updated_at
- Parent task link (clickable)
- Tags list
- Description (full text)
- Result (if set)
- Subtasks table (if any): key, title, status, assigned_to
- `QuickUpdateForm` at bottom

### `CreateTaskModal.tsx`

Ant Design `Modal` with `Form`. Fields:
- Title (required)
- Description (textarea)
- Created by (required, text input)
- Assigned to (optional — omit for backlog/mission)
- Priority (Select: critical/high/medium/low, default medium)
- Parent task key (optional)
- Tags (comma-separated text input)

On submit: `POST /api/tasks`. On success: close modal, refresh board.

### `QuickUpdateForm.tsx`

Inline form within the detail drawer:
- Status select (all 6 statuses)
- Result/notes textarea
- Update button

On submit: `PATCH /api/tasks/[key]`. On success: refresh board + drawer.

## API Routes

### `GET /api/tasks`

Query params: `?agent=` (optional filter)

```sql
SELECT t.key, t.title, t.status, t.priority, t.assigned_to, t.created_by,
       t.description, t.result, t.tags, t.created_at, t.updated_at,
       p.key AS parent_key
FROM {schema}.tasks t
LEFT JOIN {schema}.tasks p ON p.id = t.parent_task_id
WHERE ($1::text IS NULL OR t.assigned_to = $1 OR t.created_by = $1)
ORDER BY
  CASE t.priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                  WHEN 'medium' THEN 2 ELSE 3 END,
  t.created_at DESC
LIMIT 200
```

### `POST /api/tasks`

Body: `{title, description?, created_by, assigned_to?, priority?, parent_key?, tags?}`

Logic:
1. If `parent_key` provided, resolve to `parent_task_id` via SELECT
2. Generate key: `PREFIX-###` where prefix = first 3 chars of `created_by` uppercase
3. Auto-set status: `todo` if `assigned_to` set, `backlog` if not
4. INSERT and return created task

```sql
INSERT INTO {schema}.tasks (key, title, description, status, priority,
  assigned_to, created_by, parent_task_id, tags)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
RETURNING *
```

### `GET /api/tasks/[key]`

Two queries:
1. Task detail (same as list query but `WHERE t.key = $1`)
2. Subtasks: `SELECT key, title, status, priority, assigned_to FROM {schema}.tasks WHERE parent_task_id = (SELECT id FROM {schema}.tasks WHERE key = $1)`

### `PATCH /api/tasks/[key]`

Body: `{status?, result?, assigned_to?, priority?}`

```sql
UPDATE {schema}.tasks
SET status = COALESCE($2, status),
    result = COALESCE($3, result),
    assigned_to = COALESCE($4, assigned_to),
    priority = COALESCE($5, priority),
    updated_at = NOW()
WHERE key = $1
RETURNING *
```

## Types — `src/lib/types.ts`

```typescript
export interface Task {
  key: string;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  assigned_to: string | null;
  created_by: string;
  result: string | null;
  tags: string[];
  parent_key: string | null;
  created_at: string;
  updated_at: string;
}
```

## Verification

1. `/tasks` shows 6-column kanban board
2. Cards display correctly with priority colors
3. Click card → drawer opens with full detail
4. Create task → appears on board in correct column
5. Quick update → card moves to new column
6. Agent filter narrows the board
