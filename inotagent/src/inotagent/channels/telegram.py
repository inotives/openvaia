"""Telegram connector — implements the Channel protocol using python-telegram-bot (long polling)."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from inotagent.channels.base import IncomingMessage
from inotagent.channels.base import MessageHandler as AgentMessageHandler

logger = logging.getLogger(__name__)

# Telegram message limit
MAX_MESSAGE_LEN = 4096


class TelegramChannel:
    """Telegram connector implementing the Channel protocol via long polling."""

    def __init__(self, token: str, config: dict) -> None:
        self.token = token
        self.config = config
        self._handler: AgentMessageHandler | None = None
        self._app: Application | None = None
        # Track conversation_id → chat_id for sending responses
        self._conversations: dict[str, int] = {}

    def set_message_handler(self, handler: AgentMessageHandler) -> None:
        self._handler = handler

    async def start(self) -> None:
        self._app = Application.builder().token(self.token).build()

        # Register message handler for private and group messages
        self._app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self._handle_message,
        ))

        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling(drop_pending_updates=True)

        bot_info = self._app.bot
        logger.info(f"Telegram connected: @{bot_info.username} (id={bot_info.id})")

    async def stop(self) -> None:
        if self._app:
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()

    async def send(self, conversation_id: str, text: str) -> None:
        if not self._app:
            return
        chat_id = self._conversations.get(conversation_id)
        if not chat_id:
            logger.warning(f"No chat found for conversation {conversation_id}")
            return
        for chunk in split_message(text):
            await self._app.bot.send_message(chat_id=chat_id, text=chunk)

    async def send_typing(self, conversation_id: str) -> None:
        if not self._app:
            return
        chat_id = self._conversations.get(conversation_id)
        if chat_id:
            await self._app.bot.send_chat_action(chat_id=chat_id, action="typing")

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._handler or not update.message or not update.message.text:
            return

        message = update.message
        user = message.from_user
        if not user:
            return

        user_id = str(user.id)
        chat_id = message.chat_id
        chat_type = message.chat.type  # "private", "group", "supergroup"

        # In groups, only respond if bot is mentioned
        if chat_type in ("group", "supergroup"):
            bot_username = self._app.bot.username
            if bot_username and f"@{bot_username}" not in message.text:
                return

        if not self._is_allowed_user(user_id):
            return

        conversation_id = _get_conversation_id(chat_id, chat_type)
        self._conversations[conversation_id] = chat_id

        # Strip bot mention from text
        text = message.text
        if self._app and self._app.bot.username:
            text = text.replace(f"@{self._app.bot.username}", "").strip()

        sender_name = user.full_name or user.username or user_id

        incoming = IncomingMessage(
            text=text,
            sender_id=user_id,
            sender_name=sender_name,
            conversation_id=conversation_id,
            channel_type="telegram",
            raw=update,
            metadata={
                "chat_id": chat_id,
                "chat_type": chat_type,
                "message_id": message.message_id,
            },
        )

        logger.info(
            f"Telegram message from {incoming.sender_name} "
            f"(conversation={conversation_id}): {text[:100]}"
        )

        try:
            await self._app.bot.send_chat_action(chat_id=chat_id, action="typing")
            response = await self._handler(incoming)

            if response and response.strip():
                for chunk in split_message(response):
                    await message.reply_text(chunk)
            else:
                logger.warning(f"Empty response for Telegram message from {incoming.sender_name}")
        except Exception as e:
            logger.error(f"Error handling Telegram message: {e}", exc_info=True)
            try:
                await message.reply_text(f"Sorry, I encountered an error: {e}")
            except Exception:
                pass

    def _is_allowed_user(self, user_id: str) -> bool:
        """Check if a user is in the allowFrom list."""
        allow_from = self.config.get("allowFrom", [])
        if not allow_from:
            return True
        return user_id in allow_from


def _get_conversation_id(chat_id: int, chat_type: str) -> str:
    """Generate a stable conversation ID from a Telegram message."""
    if chat_type == "private":
        return f"telegram-dm-{chat_id}"
    return f"telegram-group-{chat_id}"


def split_message(text: str, max_len: int = MAX_MESSAGE_LEN) -> list[str]:
    """Split long text to fit Telegram's message limit."""
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
