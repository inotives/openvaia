"""Discord connector — implements the Channel protocol using discord.py."""

from __future__ import annotations

import logging
from typing import Any

import discord

from inotagent.channels.base import IncomingMessage, MessageHandler

logger = logging.getLogger(__name__)

# Discord message limit
MAX_MESSAGE_LEN = 2000


class DiscordChannel:
    """Discord connector implementing the Channel protocol."""

    def __init__(self, token: str, config: dict) -> None:
        self.token = token
        self.config = config  # guilds, allowFrom, requireMention, enabled
        self._handler: MessageHandler | None = None
        self._client: discord.Client | None = None
        # Track conversation_id → channel for sending responses
        self._conversations: dict[str, discord.abc.Messageable] = {}
        # Prompt gen config — set externally after init
        self._prompt_gen_config = None
        self._models: dict | None = None

    def set_message_handler(self, handler: MessageHandler) -> None:
        self._handler = handler

    def set_prompt_gen(self, config, models: dict) -> None:
        """Set prompt gen config for !prompt command."""
        self._prompt_gen_config = config
        self._models = models

    async def start(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.dm_messages = True
        self._client = discord.Client(intents=intents)

        @self._client.event
        async def on_ready() -> None:
            logger.info(f"Discord connected: {self._client.user} (id={self._client.user.id})")

        @self._client.event
        async def on_message(message: discord.Message) -> None:
            if message.author.bot:
                return
            if not self._should_respond(message):
                return
            await self._handle_message(message)

        await self._client.start(self.token)

    async def stop(self) -> None:
        if self._client:
            await self._client.close()

    async def send(self, conversation_id: str, text: str) -> None:
        target = self._conversations.get(conversation_id)
        if not target:
            logger.warning(f"No channel found for conversation {conversation_id}")
            return
        for chunk in split_message(text):
            await target.send(chunk)

    async def send_typing(self, conversation_id: str) -> None:
        target = self._conversations.get(conversation_id)
        if target:
            await target.typing()

    async def _handle_message(self, message: discord.Message) -> None:
        if not self._handler:
            logger.warning("No message handler set, ignoring message")
            return

        conversation_id = _get_conversation_id(message)
        self._conversations[conversation_id] = message.channel

        # Strip bot mention from message text
        text = message.content
        if self._client and self._client.user:
            text = text.replace(f"<@{self._client.user.id}>", "").strip()

        # Handle !prompt command — single-pass prompt enhancer
        if text.startswith("!prompt "):
            await self._handle_prompt_gen(message, text[8:].strip())
            return

        incoming = IncomingMessage(
            text=text,
            sender_id=str(message.author.id),
            sender_name=message.author.display_name,
            conversation_id=conversation_id,
            channel_type="discord",
            raw=message,
            metadata={
                "guild_id": str(message.guild.id) if message.guild else None,
                "channel_id": str(message.channel.id),
            },
        )

        logger.info(
            f"Discord message from {incoming.sender_name} "
            f"(conversation={conversation_id}): {text[:100]}"
        )

        try:
            async with message.channel.typing():
                response = await self._handler(incoming)

            if response and response.strip():
                for chunk in split_message(response):
                    await message.channel.send(chunk, reference=message)
            else:
                logger.warning(f"Empty response for Discord message from {incoming.sender_name}")
        except Exception as e:
            logger.error(f"Error handling Discord message: {e}", exc_info=True)
            try:
                await message.channel.send(f"Sorry, I encountered an error: {e}")
            except Exception:
                pass

    async def _handle_prompt_gen(self, message: discord.Message, instruction: str) -> None:
        """Handle !prompt command — enhance a rough instruction."""
        if not instruction:
            await message.channel.send("Usage: `!prompt <your rough instruction>`", reference=message)
            return

        if not self._prompt_gen_config or not self._models:
            await message.channel.send("Prompt generator not configured.", reference=message)
            return

        try:
            async with message.channel.typing():
                from inotagent.llm.prompt_gen import enhance_prompt
                enhanced, model_used = await enhance_prompt(
                    instruction, self._prompt_gen_config, self._models,
                )

            header = f"**Enhanced prompt** (via `{model_used}`):\n\n"
            for chunk in split_message(header + enhanced):
                await message.channel.send(chunk, reference=message)
        except Exception as e:
            logger.error(f"Prompt gen failed: {e}", exc_info=True)
            await message.channel.send(f"Prompt generation failed: {e}", reference=message)

    def _should_respond(self, message: discord.Message) -> bool:
        """Check if we should respond to this message based on config."""
        # DMs: check allowFrom
        if isinstance(message.channel, discord.DMChannel):
            return self._is_allowed_user(message.author.id)

        # Guild messages: check guild config
        if not message.guild:
            return False

        guild_config = self.config.get("guilds", {}).get(str(message.guild.id))
        if not guild_config:
            return False

        # Check if mention is required
        if guild_config.get("requireMention", True):
            if not self._client or not self._client.user:
                return False
            return self._client.user.mentioned_in(message)

        return True

    def _is_allowed_user(self, user_id: int) -> bool:
        """Check if a user is in the allowFrom list."""
        allow_from = self.config.get("allowFrom", [])
        if not allow_from:
            return True  # no restriction
        return str(user_id) in allow_from


def _get_conversation_id(message: discord.Message) -> str:
    """Generate a stable conversation ID from a Discord message."""
    if isinstance(message.channel, discord.Thread):
        return f"discord-thread-{message.channel.id}"
    if isinstance(message.channel, discord.DMChannel):
        return f"discord-dm-{message.author.id}"
    return f"discord-channel-{message.channel.id}"


def split_message(text: str, max_len: int = MAX_MESSAGE_LEN) -> list[str]:
    """Split long text to fit Discord's message limit.

    Splits at newlines first, then spaces, then hard-cuts as last resort.
    """
    if not text:
        return [""]
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break

        # Try to split at newline
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            # Try to split at space
            split_at = text.rfind(" ", 0, max_len)
        if split_at == -1:
            # Hard cut
            split_at = max_len

        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()

    return chunks
