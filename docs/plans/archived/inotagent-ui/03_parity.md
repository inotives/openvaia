# Phase 3: Messages + Agents + Config (Gradio Parity)

## Goal

Complete all remaining Gradio tabs. After this phase, the React UI has full feature parity with the old dashboard.

---

## Messages Page — `/messages`

### Layout

- Top: Space selector (`Select`) + message limit (`InputNumber`, 10-200, default 50) + Load button
- Middle: Message table (`Table`)
- Bottom: Send message form

### Components

**`SpaceSelector.tsx`** — Ant Design `Select` populated from `/api/spaces`. Display format: `#name (type)`.

**`MessageList.tsx`** — Ant Design `Table` with columns: From (agent name), Space, Message (body, truncated), Time (relative).

**`SendMessageForm.tsx`** — `Form` with:
- Space (Select, reuse space list)
- From agent (Input)
- Message body (TextArea)
- Send button

### API Routes

| Route | Method | SQL |
|-------|--------|-----|
| `GET /api/spaces` | GET | `SELECT id, name, type FROM {schema}.spaces ORDER BY name` |
| `GET /api/messages?space_id=&limit=` | GET | `SELECT m.id, m.from_agent, m.body, m.created_at, s.name FROM {schema}.messages m JOIN {schema}.spaces s ON s.id = m.space_id WHERE ($1::int IS NULL OR m.space_id = $1) ORDER BY m.created_at DESC LIMIT $2` |
| `POST /api/messages` | POST | `INSERT INTO {schema}.messages (space_id, from_agent, body) VALUES ($1, $2, $3) RETURNING *` |

---

## Agents Page — `/agents`

### Layout

- Top: Agent registry table
- Middle: Register new agent form
- Bottom: Health history viewer (agent selector + history table)

### Components

**`AgentTable.tsx`** — Ant Design `Table` with columns: Name, Status (tag, colored), Last Seen (relative time).

**`RegisterAgentForm.tsx`** — `Input` + `Button`. On submit: `POST /api/agents`. Uses `ON CONFLICT DO NOTHING` (idempotent).

**`HealthHistoryTable.tsx`** — Agent name `Select` + Load button. Shows Ant Design `Table` with columns: Healthy (boolean tag), Details (JSON rendered), Checked At.

### API Routes

| Route | Method | SQL |
|-------|--------|-----|
| `GET /api/agents` | GET | `SELECT name, status, last_seen FROM {schema}.agents ORDER BY name` |
| `POST /api/agents` | POST | `INSERT INTO {schema}.agents (name) VALUES ($1) ON CONFLICT DO NOTHING RETURNING *` |
| `GET /api/agents/[name]/health` | GET | `SELECT openclaw_healthy, details, checked_at FROM {schema}.agent_status WHERE agent_name = $1 ORDER BY checked_at DESC LIMIT 20` |

---

## Config Page — `/config`

### Layout

- Top: Config table with all key-value pairs
- Bottom: Upsert form + Delete button

### Components

**`ConfigTable.tsx`** — Ant Design `Table` with columns: Key, Value, Description, Updated At. Click row to populate edit form.

**`UpsertConfigForm.tsx`** — `Form` with:
- Key (Input, required)
- Value (Input, required)
- Description (Input, optional)
- Save button (upsert)
- Delete button with `Popconfirm`

### API Routes

| Route | Method | SQL |
|-------|--------|-----|
| `GET /api/config` | GET | `SELECT key, value, description, updated_at FROM {schema}.config ORDER BY key` |
| `POST /api/config` | POST | `INSERT INTO {schema}.config (key, value, description) VALUES ($1, $2, $3) ON CONFLICT (key) DO UPDATE SET value = $2, description = $3, updated_at = NOW() RETURNING *` |
| `DELETE /api/config?key=` | DELETE | `DELETE FROM {schema}.config WHERE key = $1` |

---

## Verification

1. `/messages` — select space, load messages, send a message, verify it appears
2. `/agents` — see agent list, register a new agent, view health history
3. `/config` — view config, add/update a key, delete a key
4. All 5 pages working = full Gradio parity
