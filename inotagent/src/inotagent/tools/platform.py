"""Platform tools — task management and messaging via async Postgres."""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

# Schedule tag → minutes mapping for recurring tasks
SCHEDULE_MAP = {
    "5m": 5, "15m": 15, "30m": 30,
    "hourly": 60, "4h": 240, "12h": 720,
    "daily": 1440, "weekly": 10080, "monthly": -1,  # -1 = calendar month (handled specially)
}


def parse_recurrence(tags: list[str]) -> tuple[int | None, str | None]:
    """Parse schedule:* tag into (recurrence_minutes, schedule_at).

    Supports:
    - schedule:daily        → (1440, None) — interval-based
    - schedule:daily@09:00  → (1440, '09:00') — fixed time
    - schedule:hourly       → (60, None)
    """
    for tag in tags:
        if tag.startswith("schedule:"):
            value = tag.split(":", 1)[1]
            # Check for @HH:MM suffix
            if "@" in value:
                interval_key, time_str = value.split("@", 1)
                minutes = SCHEDULE_MAP.get(interval_key)
                return minutes, time_str
            return SCHEDULE_MAP.get(value), None
    return None, None

TASK_LIST_TOOL = {
    "name": "task_list",
    "description": "List tasks with optional filters.",
    "input_schema": {
        "type": "object",
        "properties": {
            "assigned_to": {"type": "string", "description": "Filter by assigned agent"},
            "status": {
                "type": "string",
                "description": "Comma-separated status filter: todo,in_progress,blocked,review,done",
            },
            "created_by": {"type": "string", "description": "Filter by creator"},
        },
    },
}

TASK_UPDATE_TOOL = {
    "name": "task_update",
    "description": "Update a task's status, result, or other fields.",
    "input_schema": {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Task key (e.g. INO-001)"},
            "status": {"type": "string", "description": "New status"},
            "result": {"type": "string", "description": "Result or notes"},
            "assigned_to": {"type": "string", "description": "Reassign to agent"},
        },
        "required": ["key"],
    },
}

TASK_CREATE_TOOL = {
    "name": "task_create",
    "description": "Create a new task. If assigned_to is omitted, the task goes to the mission board (backlog) for any matching agent to pick up.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Task title"},
            "description": {"type": "string", "description": "Task description"},
            "assigned_to": {"type": "string", "description": "Agent to assign to (omit for mission board)"},
            "priority": {
                "type": "string",
                "enum": ["low", "medium", "high", "critical"],
                "description": "Task priority (default: medium)",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags for categorization and mission board matching",
            },
        },
        "required": ["title"],
    },
}

SEND_MESSAGE_TOOL = {
    "name": "send_message",
    "description": "Send a message to a space (channel).",
    "input_schema": {
        "type": "object",
        "properties": {
            "space_name": {"type": "string", "description": "Space name (e.g. 'public', 'tasks')"},
            "body": {"type": "string", "description": "Message body"},
        },
        "required": ["space_name", "body"],
    },
}

SKILL_CREATE_TOOL = {
    "name": "skill_create",
    "description": (
        "Propose a new skill as a draft. Draft skills require human approval before activation. "
        "Use this when you notice a repeatable pattern, recurring correction, or workflow worth formalizing."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Skill name (snake_case, e.g. research_report_format)"},
            "description": {"type": "string", "description": "One-line description of what this skill teaches"},
            "content": {"type": "string", "description": "Skill content in markdown — the knowledge to inject into system prompt"},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags for categorization (e.g. research, coding, workflow)",
            },
        },
        "required": ["name", "description", "content", "tags"],
    },
}

SKILL_PROPOSE_TOOL = {
    "name": "skill_propose",
    "description": (
        "Propose a skill evolution for human review. Use when you identify: "
        "a broken/outdated skill (type=fix), an opportunity to combine skills (type=derived), "
        "or a novel reusable pattern (type=captured). All proposals require human approval."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "enum": ["fix", "derived", "captured"],
                "description": "fix=repair broken skill, derived=enhance/combine, captured=new pattern",
            },
            "skill_name": {
                "type": "string",
                "description": "For fix/derived: name of existing skill to evolve. For captured: leave empty.",
            },
            "proposed_name": {
                "type": "string",
                "description": "For captured: name for the new skill. For fix/derived: leave empty.",
            },
            "direction": {
                "type": "string",
                "description": "What to change and why — the rationale for this evolution",
            },
            "proposed_content": {
                "type": "string",
                "description": "Full proposed skill content in markdown",
            },
            "proposed_tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags for the proposed skill (for captured/derived)",
            },
        },
        "required": ["type", "direction", "proposed_content"],
    },
}

SKILL_EQUIP_TOOL = {
    "name": "skill_equip",
    "description": (
        "Load a skill into your current conversation context. Use when you need a skill "
        "that isn't currently loaded — e.g., you're mid-task and encounter a security concern. "
        "Only affects this conversation, not persistent."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Skill name to load (e.g. 'security_audit')"},
        },
        "required": ["name"],
    },
}

PLATFORM_TOOLS = [TASK_LIST_TOOL, TASK_UPDATE_TOOL, TASK_CREATE_TOOL, SEND_MESSAGE_TOOL, SKILL_CREATE_TOOL, SKILL_PROPOSE_TOOL, SKILL_EQUIP_TOOL]

_DB_NOT_CONNECTED = "Error: Database not connected. Platform tools require a running Postgres instance."


class PlatformTools:
    """Platform tool handlers backed by async Postgres."""

    def __init__(self, agent_name: str, db_available: bool = False) -> None:
        self.agent_name = agent_name
        self.db_available = db_available

    def _check_db(self) -> str | None:
        if not self.db_available:
            return _DB_NOT_CONNECTED
        return None

    async def task_list(
        self,
        assigned_to: str | None = None,
        status: str | None = None,
        created_by: str | None = None,
    ) -> str:
        if err := self._check_db():
            return err

        from inotagent.db.pool import get_connection, get_schema
        schema = get_schema()

        conditions: list[str] = []
        params: list = []

        if assigned_to:
            conditions.append("t.assigned_to = %s")
            params.append(assigned_to)
        if created_by:
            conditions.append("t.created_by = %s")
            params.append(created_by)
        if status:
            statuses = [s.strip() for s in status.split(",")]
            conditions.append("t.status = ANY(%s)")
            params.append(statuses)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        async with get_connection() as conn:
            cur = await conn.execute(
                f"""SELECT t.key, t.title, t.status, t.priority, t.assigned_to,
                           t.created_by, COALESCE(p.key, '-') AS parent_key
                    FROM {schema}.tasks t
                    LEFT JOIN {schema}.tasks p ON t.parent_task_id = p.id
                    {where}
                    ORDER BY
                        CASE t.priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                             WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END,
                        t.created_at DESC
                    LIMIT 50""",
                params,
            )
            rows = await cur.fetchall()

        if not rows:
            return "No tasks found."

        lines = []
        for r in rows:
            lines.append(
                f"[{r['key']}] {r['title']} | status={r['status']} "
                f"priority={r['priority']} assigned={r['assigned_to']} "
                f"created_by={r['created_by']} parent={r['parent_key']}"
            )
        return "\n".join(lines)

    async def task_update(
        self,
        key: str,
        status: str | None = None,
        result: str | None = None,
        assigned_to: str | None = None,
    ) -> str:
        if err := self._check_db():
            return err

        from inotagent.db.pool import get_connection, get_schema
        schema = get_schema()

        fields: dict[str, str] = {}
        if status:
            fields["status"] = status
        if result:
            fields["result"] = result
        if assigned_to:
            fields["assigned_to"] = assigned_to

        if not fields:
            return "Error: No fields to update."

        set_clauses = [f"{k} = %s" for k in fields]
        set_clauses.append("updated_at = NOW()")
        if status in ("done", "review"):
            set_clauses.append("last_completed_at = NOW()")
        values = list(fields.values()) + [key]

        async with get_connection() as conn:
            cur = await conn.execute(
                f"UPDATE {schema}.tasks SET {', '.join(set_clauses)} WHERE key = %s RETURNING key, title, status",
                values,
            )
            row = await cur.fetchone()

        if not row:
            return f"Error: Task '{key}' not found."
        return f"Updated {row['key']}: {row['title']} → status={row['status']}"

    async def task_create(
        self,
        title: str,
        assigned_to: str | None = None,
        description: str | None = None,
        priority: str = "medium",
        tags: list[str] | None = None,
    ) -> str:
        if err := self._check_db():
            return err

        from inotagent.db.pool import get_connection, get_schema
        schema = get_schema()

        # Unassigned tasks go to backlog (mission board)
        status = "todo" if assigned_to else "backlog"

        async with get_connection() as conn:
            # Generate task key
            cur = await conn.execute(f"SELECT nextval('{schema}.task_key_seq')")
            row = await cur.fetchone()
            seq = row["nextval"]
            prefix = self.agent_name[:3].upper()
            key = f"{prefix}-{seq:03d}"

            recurrence, schedule_at = parse_recurrence(tags or [])
            await conn.execute(
                f"""INSERT INTO {schema}.tasks
                    (key, title, description, created_by, assigned_to, priority, status, tags, recurrence_minutes, schedule_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (key, title, description, self.agent_name, assigned_to, priority, status, tags or [], recurrence, schedule_at),
            )

        if assigned_to:
            return f"Created task {key}: {title} (assigned to {assigned_to}, priority={priority})"
        return f"Created mission {key}: {title} (backlog, tags={tags or []}, priority={priority})"

    async def send_message(self, space_name: str, body: str) -> str:
        if err := self._check_db():
            return err

        from inotagent.db.pool import get_connection, get_schema
        schema = get_schema()

        async with get_connection() as conn:
            cur = await conn.execute(
                f"SELECT id FROM {schema}.spaces WHERE name = %s",
                (space_name,),
            )
            space = await cur.fetchone()
            if not space:
                return f"Error: Space '{space_name}' not found."

            await conn.execute(
                f"INSERT INTO {schema}.messages (from_agent, space_id, body) VALUES (%s, %s, %s)",
                (self.agent_name, space["id"], body),
            )

        return f"Message sent to #{space_name}."

    async def skill_create(
        self,
        name: str,
        description: str,
        content: str,
        tags: list[str],
    ) -> str:
        """Create a draft skill for human review."""
        if not self.db_available:
            return _DB_NOT_CONNECTED

        from inotagent.db.pool import get_connection, get_schema
        schema = get_schema()
        async with get_connection() as conn:
            # Check if skill name already exists
            cur = await conn.execute(
                f"SELECT id FROM {schema}.skills WHERE name = %s", (name,)
            )
            if await cur.fetchone():
                return f"Error: Skill '{name}' already exists. Choose a different name."

            await conn.execute(
                f"""INSERT INTO {schema}.skills (name, description, content, tags, global, enabled, status, created_by)
                    VALUES (%s, %s, %s, %s, false, true, 'draft', %s)""",
                (name, description, content, tags, self.agent_name),
            )

        return f"Draft skill '{name}' created. It will be reviewed by a human before activation."

    async def skill_propose(
        self,
        type: str,
        direction: str,
        proposed_content: str,
        skill_name: str | None = None,
        proposed_name: str | None = None,
        proposed_tags: list[str] | None = None,
    ) -> str:
        """Submit a skill evolution proposal for human review."""
        if not self.db_available:
            return _DB_NOT_CONNECTED

        if type not in ("fix", "derived", "captured"):
            return "Error: type must be 'fix', 'derived', or 'captured'"

        from inotagent.db.pool import get_connection, get_schema
        schema = get_schema()

        skill_id = None
        if type in ("fix", "derived") and skill_name:
            async with get_connection() as conn:
                cur = await conn.execute(
                    f"SELECT id FROM {schema}.skills WHERE name = %s", (skill_name,)
                )
                row = await cur.fetchone()
                if not row:
                    return f"Error: Skill '{skill_name}' not found"
                skill_id = row["id"]

        if type == "captured" and not proposed_name:
            return "Error: proposed_name is required for captured proposals"

        async with get_connection() as conn:
            await conn.execute(
                f"""INSERT INTO {schema}.skill_evolution_proposals
                    (skill_id, evolution_type, proposed_by, status, direction,
                     proposed_content, proposed_name, proposed_description, proposed_tags)
                    VALUES (%s, %s, %s, 'pending', %s, %s, %s, %s, %s)""",
                (
                    skill_id, type, self.agent_name, direction,
                    proposed_content, proposed_name,
                    direction[:200] if type == "captured" else None,
                    proposed_tags or [],
                ),
            )

        label = f"'{skill_name}'" if skill_name else f"new skill '{proposed_name}'"
        return f"Evolution proposal ({type}) for {label} submitted. Awaiting human review."

    async def skill_equip(self, name: str) -> str:
        """Load a skill into the current conversation context on-demand."""
        if not self.db_available:
            return _DB_NOT_CONNECTED

        from inotagent.db.skills import load_skill_by_name
        skill = await load_skill_by_name(name)
        if not skill:
            return f"Error: Skill '{name}' not found or not active."

        # Inject into the agent's current skill set (non-persistent)
        if hasattr(self, '_agent_config') and self._agent_config:
            if name not in self._agent_config._skill_names:
                self._agent_config._skill_ids.append(skill["id"])
                self._agent_config._skill_names.append(skill["name"])
                self._agent_config._skill_content += "\n\n" + skill["content"]

        return f"Skill '{name}' loaded into current conversation. Content:\n\n{skill['content'][:500]}..."
