"""Conversation history — store and retrieve messages per conversation."""

from __future__ import annotations

import json
import logging

from inotagent.db.pool import get_connection, get_schema
from inotagent.llm.client import LLMMessage, ToolCall

logger = logging.getLogger(__name__)

# Max chars for tool results stored in DB (full output is never re-sent on future turns)
MAX_TOOL_RESULT_CHARS = 2000


def truncate_tool_result(result: str) -> str:
    """Truncate tool output before storing in conversation history."""
    if len(result) <= MAX_TOOL_RESULT_CHARS:
        return result
    half = MAX_TOOL_RESULT_CHARS // 2
    return (
        result[:half]
        + f"\n\n... [{len(result) - MAX_TOOL_RESULT_CHARS} chars truncated] ...\n\n"
        + result[-half:]
    )


async def save_message(
    conversation_id: str,
    agent_name: str,
    role: str,
    content: str,
    channel_type: str = "cli",
    tool_calls: list[ToolCall] | None = None,
    tool_call_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Save a message to conversation history."""
    schema = get_schema()

    # Truncate tool results before storing
    stored_content = content
    if role == "tool":
        stored_content = truncate_tool_result(content)

    tc_json = None
    if tool_calls:
        tc_json = json.dumps([
            {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
            for tc in tool_calls
        ])

    meta = json.dumps({
        **(metadata or {}),
        **({"tool_call_id": tool_call_id} if tool_call_id else {}),
    })

    async with get_connection() as conn:
        await conn.execute(
            f"""INSERT INTO {schema}.conversations
                (conversation_id, agent_name, role, content, channel_type, tool_calls, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (conversation_id, agent_name, role, stored_content, channel_type, tc_json, meta),
        )


async def load_history(
    conversation_id: str,
    limit: int = 100,
) -> list[LLMMessage]:
    """Load recent messages for a conversation, ordered oldest first."""
    schema = get_schema()
    async with get_connection() as conn:
        cur = await conn.execute(
            f"""SELECT role, content, tool_calls, metadata
                FROM {schema}.conversations
                WHERE conversation_id = %s
                ORDER BY created_at DESC
                LIMIT %s""",
            (conversation_id, limit),
        )
        rows = await cur.fetchall()

    # Reverse to get chronological order
    messages = []
    for row in reversed(rows):
        tool_calls_list = None
        if row["tool_calls"]:
            tc_data = row["tool_calls"] if isinstance(row["tool_calls"], list) else json.loads(row["tool_calls"])
            tool_calls_list = [
                ToolCall(id=tc["id"], name=tc["name"], arguments=tc["arguments"])
                for tc in tc_data
            ]

        tool_call_id = None
        if row["metadata"]:
            meta = row["metadata"] if isinstance(row["metadata"], dict) else json.loads(row["metadata"])
            tool_call_id = meta.get("tool_call_id")

        messages.append(LLMMessage(
            role=row["role"],
            content=row["content"] or "",
            tool_calls=tool_calls_list,
            tool_call_id=tool_call_id,
        ))

    return messages


async def list_conversations(
    agent_name: str,
    limit: int = 20,
) -> list[dict]:
    """List recent conversations with last message preview."""
    schema = get_schema()
    async with get_connection() as conn:
        cur = await conn.execute(
            f"""SELECT DISTINCT ON (conversation_id)
                    conversation_id, channel_type, content, created_at
                FROM {schema}.conversations
                WHERE agent_name = %s
                ORDER BY conversation_id, created_at DESC""",
            (agent_name,),
        )
        rows = await cur.fetchall()

    return [
        {
            "conversation_id": r["conversation_id"],
            "channel_type": r["channel_type"],
            "last_message": (r["content"] or "")[:100],
            "last_at": r["created_at"],
        }
        for r in sorted(rows, key=lambda r: r["created_at"], reverse=True)[:limit]
    ]


async def prune_conversations(retention_days: int = 30) -> int:
    """Delete conversations older than retention period. Returns count deleted."""
    schema = get_schema()
    async with get_connection() as conn:
        cur = await conn.execute(
            f"DELETE FROM {schema}.conversations WHERE created_at < NOW() - INTERVAL '%s days'",
            (retention_days,),
        )
        return cur.rowcount
