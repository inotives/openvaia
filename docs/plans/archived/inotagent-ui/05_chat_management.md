# Phase 5: Agent Chat + Agent Management

## Goal

Two new feature pages:
1. Chat with agents directly from the dashboard (via platform.messages)
2. Manage agent lifecycle: create, edit, view repos, deregister

---

## Agent Chat — `/chat`

### How It Works

The chat interface uses the existing `platform.messages` + `platform.spaces` tables. When a user sends a message:

1. Find or create a `direct` space between `operator` (the UI user) and the target agent
2. Insert the message into that space
3. The agent's inotagent heartbeat picks it up on next cycle
4. Poll for responses (or receive via SSE from Phase 4)

This is **not instant** — response time depends on the agent's polling interval (~60s). The UI shows a "waiting for response" indicator.

### Layout

- Left sidebar: Agent selector (list of online agents)
- Main area: Chat window with message bubbles
- Bottom: Input bar with send button

### Components

**`AgentSelector.tsx`** — Vertical list of agents with online/offline indicators. Click to select. Shows unread count badge.

**`ChatWindow.tsx`** — Scrollable message area. Messages grouped by timestamp. Auto-scrolls to bottom on new messages. Shows "Agent is processing..." indicator when waiting.

**`MessageBubble.tsx`** — Individual message. Left-aligned for agent messages, right-aligned for operator messages. Shows: body, timestamp, agent name/avatar.

### API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `POST /api/chat` | POST | Send message to agent |
| `GET /api/chat/history?agent=&limit=` | GET | Get conversation history |

**`POST /api/chat`** — Body: `{agent_name, body}`

Logic:
1. Find direct space between `operator` and `agent_name`:
   ```sql
   SELECT s.id FROM {schema}.spaces s
   JOIN {schema}.space_members sm1 ON sm1.space_id = s.id AND sm1.agent_name = 'operator'
   JOIN {schema}.space_members sm2 ON sm2.space_id = s.id AND sm2.agent_name = $1
   WHERE s.type = 'direct'
   LIMIT 1
   ```
2. If no space exists, create one + add both members
3. Insert message:
   ```sql
   INSERT INTO {schema}.messages (space_id, from_agent, body)
   VALUES ($1, 'operator', $2) RETURNING *
   ```

**`GET /api/chat/history`**:
```sql
SELECT m.from_agent, m.body, m.created_at
FROM {schema}.messages m
JOIN {schema}.spaces s ON s.id = m.space_id
JOIN {schema}.space_members sm1 ON sm1.space_id = s.id AND sm1.agent_name = 'operator'
JOIN {schema}.space_members sm2 ON sm2.space_id = s.id AND sm2.agent_name = $1
WHERE s.type = 'direct'
ORDER BY m.created_at ASC
LIMIT $2
```

### SSE Integration

Subscribe to `new-message` events. When a message arrives in the active chat space, append it to the chat window without manual refresh.

---

## Agent Management — `/management`

### Layout

- Agent table (expandable rows)
- Create new agent section
- Per-agent detail panel with repo management

### Components

**`AgentDetailPanel.tsx`** — Expandable row content showing:
- Agent config summary (model, status, last_seen)
- Assigned repos table
- Action buttons: deregister (with confirmation)

**`AgentRepoTable.tsx`** — Ant Design `Table` showing repos assigned to this agent:
- Columns: name, repo_url, assigned_by, assigned_at
- Remove button per row (with `Popconfirm`)
- Add repo form at bottom (URL input + name input + Add button)

**`CreateAgentForm.tsx`** — `Form` with:
- Agent name (required)
- Register button
- Note: This registers the agent in DB. Actual Docker deployment is a manual step (documented).

### API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `GET /api/management/agents` | GET | All agents with repo count + health |
| `PATCH /api/management/agents/[name]` | PATCH | Update agent status |
| `DELETE /api/management/agents/[name]` | DELETE | Deregister agent |
| `GET /api/management/agents/[name]/repos` | GET | Agent's assigned repos |
| `POST /api/management/agents/[name]/repos` | POST | Assign repo |
| `DELETE /api/management/agents/[name]/repos?url=` | DELETE | Remove repo |

**`GET /api/management/agents`**:
```sql
SELECT a.name, a.status, a.last_seen,
       (SELECT COUNT(*) FROM {schema}.agent_repos WHERE agent_name = a.name) AS repo_count,
       s.openclaw_healthy, s.details
FROM {schema}.agents a
LEFT JOIN LATERAL (
    SELECT openclaw_healthy, details
    FROM {schema}.agent_status WHERE agent_name = a.name
    ORDER BY checked_at DESC LIMIT 1
) s ON true
ORDER BY a.name
```

**`GET /api/management/agents/[name]/repos`**:
```sql
SELECT name, repo_url, assigned_by, created_at
FROM {schema}.agent_repos
WHERE agent_name = $1
ORDER BY name
```

**`POST /api/management/agents/[name]/repos`** — Body: `{name, repo_url, assigned_by}`:
```sql
INSERT INTO {schema}.agent_repos (agent_name, name, repo_url, assigned_by)
VALUES ($1, $2, $3, $4)
ON CONFLICT DO NOTHING RETURNING *
```

**`DELETE /api/management/agents/[name]/repos?url=`**:
```sql
DELETE FROM {schema}.agent_repos
WHERE agent_name = $1 AND repo_url = $2
```

### Scope Note

Container lifecycle (deploy, restart, stop) requires Docker socket access — out of scope for this phase. The management page handles DB-level operations only. Container management can be added later via a Docker API integration.

---

## Verification

1. `/chat` — select an agent, send a message, verify it appears in DB
2. `/chat` — if agent responds (via inotagent), message appears in chat
3. `/management` — see all agents with repo counts
4. `/management` — expand agent, view repos, add/remove a repo
5. `/management` — register new agent, deregister an agent
