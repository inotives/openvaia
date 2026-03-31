"""Agent reasoning loop — the core of inotagent."""

from __future__ import annotations

import asyncio
import logging

from inotagent.config.agent import AgentConfig
from inotagent.config.models import ModelConfig
from inotagent.llm.client import LLMMessage, LLMResponse, ToolCall
from inotagent.llm.factory import chat_with_fallback
from inotagent.llm.tokens import build_context
from inotagent.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# Maximum tool call iterations to prevent infinite loops
MAX_TOOL_ITERATIONS = 25


class AgentLoop:
    """Core agent loop: receive message → build prompt → call LLM → execute tools → return response.

    Supports two modes:
    - Stateless: caller passes history (CLI mode, simple use)
    - Persistent: conversation_id triggers DB load/save (channel mode)
    """

    def __init__(
        self,
        config: AgentConfig,
        models: dict[str, ModelConfig],
        tool_registry: ToolRegistry | None = None,
        db_available: bool = False,
    ):
        self.config = config
        self.models = models
        self.tool_registry = tool_registry
        self.db_available = db_available
        self._semaphore = asyncio.Semaphore(1 if not config.parallel else 5)
        self._active_count = 0

    def is_busy(self) -> bool:
        """True if agent is currently processing a conversation."""
        return self._active_count > 0

    async def run(
        self,
        message: str,
        history: list[LLMMessage] | None = None,
        conversation_id: str | None = None,
        channel_type: str = "cli",
        skip_save_user: bool = False,
    ) -> str:
        """Process a message through the agent loop.

        If conversation_id is provided and DB is available, history is loaded
        from DB and the exchange is saved after completion.

        Otherwise, uses the provided history list (stateless mode).

        If skip_save_user is True, the user message is assumed to already
        exist in DB (e.g. web chat) and won't be re-saved or duplicated.
        """
        async with self._semaphore:
            self._active_count += 1
            try:
                return await self._run_inner(message, history, conversation_id, channel_type, skip_save_user)
            finally:
                self._active_count -= 1

    async def _run_inner(
        self,
        message: str,
        history: list[LLMMessage] | None = None,
        conversation_id: str | None = None,
        channel_type: str = "cli",
        skip_save_user: bool = False,
    ) -> str:
        from datetime import UTC, datetime
        model_config = self.models[self.config.model_id]
        today = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        system = self.config.system_prompt_with_skills + f"\n\n## Current Time\n- {today}"

        # Load history from DB if conversation_id is provided
        if conversation_id and self.db_available:
            from inotagent.db.conversations import load_history, save_message
            db_history = await load_history(conversation_id)

            if skip_save_user:
                # User message already in DB (web chat) — history includes it
                messages = db_history
            else:
                messages = db_history + [LLMMessage(role="user", content=message)]
                # Save user message to DB with skill metadata
                skill_meta = None
                if self.config._skill_ids:
                    skill_meta = {
                        "skills": self.config._skill_names,
                        "model": self.config.model_id,
                    }
                await save_message(
                    conversation_id=conversation_id,
                    agent_name=self.config.name,
                    role="user",
                    content=message,
                    channel_type=channel_type,
                    metadata=skill_meta,
                )
        else:
            messages = list(history or []) + [LLMMessage(role="user", content=message)]
            save_message = None  # type: ignore[assignment]

        # Get tool definitions if registry is available
        tools = self.tool_registry.get_definitions() if self.tool_registry and self.tool_registry.has_tools() else None

        # Truncate history to fit context window
        user_msg = messages[-1]
        truncated_history = build_context(
            system=system,
            history=messages,
            tools=tools,
            model_config=model_config,
        )
        # Ensure the current user message is always included
        if not truncated_history or truncated_history[-1] is not user_msg:
            truncated_history = truncated_history + [user_msg]
        messages = truncated_history

        logger.info(
            f"[{self.config.name}] Calling {self.config.model_id} "
            f"({len(messages)} messages, system={len(system)} chars, "
            f"tools={len(tools) if tools else 0})"
        )

        response = await chat_with_fallback(
            models=self.models,
            model_id=self.config.model_id,
            fallbacks=self.config.fallbacks,
            system=system,
            messages=messages,
            tools=tools,
            max_tokens=model_config.max_tokens,
        )

        logger.info(
            f"[{self.config.name}] Response: {response.usage.total_tokens} tokens "
            f"(in={response.usage.input_tokens}, out={response.usage.output_tokens})"
        )

        # Detect autonomous conversations (triggered by idle heartbeat)
        is_autonomous = conversation_id and conversation_id.startswith("heartbeat-idle-")

        # Tool call loop
        iterations = 0
        while response.tool_calls and self.tool_registry and iterations < MAX_TOOL_ITERATIONS:
            iterations += 1

            # Autonomous interrupt: check for pending human messages between iterations
            # Checks: (1) web chat messages in DB, (2) other channels waiting at semaphore
            if is_autonomous and iterations > 1:
                has_human_msg = await self._check_pending_human_messages(conversation_id)
                has_queued = self._semaphore._value == 0 and len(self._semaphore._waiters) > 0
                if has_human_msg or has_queued:
                    logger.info(
                        f"[{self.config.name}] Autonomous task interrupted — "
                        f"human message detected (iter {iterations})"
                    )
                    # Save a note about the interruption
                    if conversation_id and self.db_available:
                        from inotagent.db.conversations import save_message
                        await save_message(
                            conversation_id=conversation_id,
                            agent_name=self.config.name,
                            role="assistant",
                            content="[Autonomous task paused — prioritizing incoming human message]",
                            channel_type=channel_type,
                        )
                    return "[Paused: human message received]"

            # Add assistant message with tool calls to conversation
            messages.append(LLMMessage(
                role="assistant",
                content=response.content,
                tool_calls=response.tool_calls,
            ))

            # Save assistant message with tool calls to DB
            if conversation_id and self.db_available:
                from inotagent.db.conversations import save_message
                await save_message(
                    conversation_id=conversation_id,
                    agent_name=self.config.name,
                    role="assistant",
                    content=response.content,
                    channel_type=channel_type,
                    tool_calls=response.tool_calls,
                    metadata=_usage_meta(response, self.config.model_id),
                )

            # Execute each tool call and collect results
            for tc in response.tool_calls:
                logger.info(f"[{self.config.name}] Tool call: {tc.name}({_summarize_args(tc.arguments)})")
                result = await self.tool_registry.execute(tc.name, tc.arguments)
                logger.info(f"[{self.config.name}] Tool result ({tc.name}): {len(result)} chars")
                messages.append(LLMMessage(
                    role="tool",
                    content=result,
                    tool_call_id=tc.id,
                ))

                # Save tool result to DB (truncated)
                if conversation_id and self.db_available:
                    from inotagent.db.conversations import save_message
                    await save_message(
                        conversation_id=conversation_id,
                        agent_name=self.config.name,
                        role="tool",
                        content=result,
                        channel_type=channel_type,
                        tool_call_id=tc.id,
                    )

            # Call LLM again with tool results
            response = await chat_with_fallback(
                models=self.models,
                model_id=self.config.model_id,
                fallbacks=self.config.fallbacks,
                system=system,
                messages=messages,
                tools=tools,
                max_tokens=model_config.max_tokens,
            )

            logger.info(
                f"[{self.config.name}] Response (iter {iterations}): "
                f"{response.usage.total_tokens} tokens"
            )

        if iterations >= MAX_TOOL_ITERATIONS:
            logger.warning(f"[{self.config.name}] Hit max tool iterations ({MAX_TOOL_ITERATIONS})")

        # Save final assistant response to DB
        if conversation_id and self.db_available:
            from inotagent.db.conversations import save_message
            await save_message(
                conversation_id=conversation_id,
                agent_name=self.config.name,
                role="assistant",
                content=response.content,
                channel_type=channel_type,
                metadata=_usage_meta(response, self.config.model_id),
            )

        # Update skill metrics — track usage
        if self.db_available and self.config._skill_ids:
            await self._update_skill_metrics(iterations > 0)

        return response.content

    async def _update_skill_metrics(self, had_tool_calls: bool) -> None:
        """Update skill quality metrics after a conversation completes."""
        try:
            from inotagent.db.pool import get_connection, get_schema
            schema = get_schema()
            skill_ids = self.config._skill_ids
            agent_name = self.config.name

            async with get_connection() as conn:
                for skill_id in skill_ids:
                    # Upsert: increment times_selected, times_completed
                    await conn.execute(
                        f"""INSERT INTO {schema}.skill_metrics
                                (skill_id, agent_name, times_selected, times_completed, last_applied_at)
                            VALUES (%s, %s, 1, %s, NOW())
                            ON CONFLICT (skill_id, agent_name) DO UPDATE SET
                                times_selected = {schema}.skill_metrics.times_selected + 1,
                                times_completed = {schema}.skill_metrics.times_completed + %s,
                                last_applied_at = NOW(),
                                updated_at = NOW()""",
                        (skill_id, agent_name, 1 if had_tool_calls else 0, 1 if had_tool_calls else 0),
                    )
        except Exception as e:
            logger.debug(f"Skill metrics update failed: {e}")

    async def _check_pending_human_messages(self, current_conversation_id: str) -> bool:
        """Check if there are unprocessed human messages waiting (any channel)."""
        if not self.db_available:
            return False
        try:
            from inotagent.db.pool import get_connection, get_schema
            schema = get_schema()
            async with get_connection() as conn:
                cur = await conn.execute(
                    f"""SELECT 1 FROM {schema}.conversations
                        WHERE agent_name = %s
                          AND role = 'user'
                          AND processed_at IS NULL
                          AND channel_type = 'web'
                          AND conversation_id != %s
                        LIMIT 1""",
                    (self.config.name, current_conversation_id),
                )
                row = await cur.fetchone()
            return row is not None
        except Exception as e:
            logger.debug(f"Human message check failed: {e}")
            return False


def _usage_meta(response: LLMResponse, model_id: str) -> dict:
    """Build metadata dict with token usage from an LLM response."""
    return {
        "model": model_id,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "total_tokens": response.usage.total_tokens,
    }


def _summarize_args(args: dict) -> str:
    """Summarize tool arguments for logging (truncate long values)."""
    parts = []
    for k, v in args.items():
        s = str(v)
        if len(s) > 80:
            s = s[:77] + "..."
        parts.append(f"{k}={s}")
    return ", ".join(parts)
