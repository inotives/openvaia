"""Slack connector — implements the Channel protocol using slack-bolt (Socket Mode)."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient

from inotagent.channels.base import IncomingMessage, MessageHandler

logger = logging.getLogger(__name__)

# Slack message limit
MAX_MESSAGE_LEN = 4000


class SlackChannel:
    """Slack connector implementing the Channel protocol via Socket Mode."""

    def __init__(self, bot_token: str, app_token: str, config: dict) -> None:
        self.bot_token = bot_token
        self.app_token = app_token
        self.config = config
        self._handler: MessageHandler | None = None
        self._app: AsyncApp | None = None
        self._socket_handler: AsyncSocketModeHandler | None = None
        self._bot_user_id: str | None = None
        # Track conversation_id → (channel_id, thread_ts) for sending responses
        self._conversations: dict[str, tuple[str, str | None]] = {}

    def set_message_handler(self, handler: MessageHandler) -> None:
        self._handler = handler

    async def start(self) -> None:
        self._app = AsyncApp(token=self.bot_token)

        # Resolve bot user ID
        client = AsyncWebClient(token=self.bot_token)
        auth = await client.auth_test()
        self._bot_user_id = auth["user_id"]
        logger.info(f"Slack connected: bot_user_id={self._bot_user_id}")

        # Register event handlers
        @self._app.event("app_mention")
        async def handle_mention(event: dict, say: Any) -> None:
            await self._handle_event(event, reply_in_thread=True)

        @self._app.event("message")
        async def handle_message(event: dict, say: Any) -> None:
            # Skip bot messages, message_changed, etc.
            if event.get("subtype"):
                return
            # Skip if this is a channel message (not DM) without mention
            # app_mention handler covers channel mentions
            channel_type = event.get("channel_type", "")
            if channel_type != "im":
                return
            await self._handle_event(event, reply_in_thread=False)

        self._socket_handler = AsyncSocketModeHandler(self._app, self.app_token)
        await self._socket_handler.start_async()

    async def stop(self) -> None:
        if self._socket_handler:
            await self._socket_handler.close_async()

    async def send(self, conversation_id: str, text: str) -> None:
        if not self._app:
            return
        target = self._conversations.get(conversation_id)
        if not target:
            logger.warning(f"No channel found for conversation {conversation_id}")
            return
        channel_id, thread_ts = target
        for chunk in split_message(text):
            await self._app.client.chat_postMessage(
                channel=channel_id,
                text=chunk,
                thread_ts=thread_ts,
            )

    async def send_typing(self, conversation_id: str) -> None:
        # Slack doesn't have a persistent typing indicator API for bots
        pass

    async def _handle_event(self, event: dict, reply_in_thread: bool) -> None:
        if not self._handler:
            logger.warning("No message handler set, ignoring Slack event")
            return

        user_id = event.get("user", "")
        if not user_id or user_id == self._bot_user_id:
            return

        if not self._is_allowed_user(user_id):
            return

        channel_id = event.get("channel", "")
        channel_type = event.get("channel_type", "")
        thread_ts = event.get("thread_ts") or (event.get("ts") if reply_in_thread else None)

        conversation_id = _get_conversation_id(channel_id, channel_type, thread_ts)
        self._conversations[conversation_id] = (channel_id, thread_ts)

        # Strip bot mention from text
        text = event.get("text", "")
        if self._bot_user_id:
            text = re.sub(rf"<@{self._bot_user_id}>", "", text).strip()

        # Resolve user display name
        sender_name = user_id
        if self._app:
            try:
                user_info = await self._app.client.users_info(user=user_id)
                profile = user_info["user"]["profile"]
                sender_name = profile.get("display_name") or profile.get("real_name") or user_id
            except Exception:
                pass

        incoming = IncomingMessage(
            text=text,
            sender_id=user_id,
            sender_name=sender_name,
            conversation_id=conversation_id,
            channel_type="slack",
            raw=event,
            metadata={
                "channel_id": channel_id,
                "channel_type": channel_type,
                "thread_ts": thread_ts,
            },
        )

        logger.info(
            f"Slack message from {incoming.sender_name} "
            f"(conversation={conversation_id}): {text[:100]}"
        )

        try:
            response = await self._handler(incoming)

            if response and response.strip():
                for chunk in split_message(response):
                    await self._app.client.chat_postMessage(
                        channel=channel_id,
                        text=chunk,
                        thread_ts=thread_ts,
                    )
            else:
                logger.warning(f"Empty response for Slack message from {incoming.sender_name}")
        except Exception as e:
            logger.error(f"Error handling Slack message: {e}", exc_info=True)
            try:
                await self._app.client.chat_postMessage(
                    channel=channel_id,
                    text=f"Sorry, I encountered an error: {e}",
                    thread_ts=thread_ts,
                )
            except Exception:
                pass

    def _is_allowed_user(self, user_id: str) -> bool:
        """Check if a user is in the allowFrom list."""
        allow_from = self.config.get("allowFrom", [])
        if not allow_from:
            return True
        return user_id in allow_from


def _get_conversation_id(channel_id: str, channel_type: str, thread_ts: str | None) -> str:
    """Generate a stable conversation ID from a Slack event."""
    if thread_ts:
        return f"slack-thread-{channel_id}-{thread_ts}"
    if channel_type == "im":
        return f"slack-dm-{channel_id}"
    return f"slack-channel-{channel_id}"


def split_message(text: str, max_len: int = MAX_MESSAGE_LEN) -> list[str]:
    """Split long text to fit Slack's message limit."""
    if not text:
        return [""]
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break

        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = text.rfind(" ", 0, max_len)
        if split_at == -1:
            split_at = max_len

        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()

    return chunks
