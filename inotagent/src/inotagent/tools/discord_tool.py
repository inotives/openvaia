"""Discord send tool — allows agents to proactively send messages to Discord channels."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

DISCORD_SEND_TOOL = {
    "name": "discord_send",
    "description": (
        "Send a message to a Discord channel. Use this to notify humans of task progress, "
        "completions, or blockers. Requires a channel ID."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "channel_id": {
                "type": "string",
                "description": "Discord channel ID to send the message to",
            },
            "message": {
                "type": "string",
                "description": "Message text to send",
            },
        },
        "required": ["channel_id", "message"],
    },
}


class DiscordSendTool:
    """Tool for agents to proactively send Discord messages."""

    def __init__(self) -> None:
        self._client = None  # discord.Client, injected after setup

    def set_client(self, client) -> None:
        """Inject the discord.py client after channel setup."""
        self._client = client
        logger.info("DiscordSendTool: client injected")

    async def execute(self, channel_id: str, message: str) -> str:
        if not self._client:
            return "Error: Discord not connected. Cannot send message."

        try:
            channel = self._client.get_channel(int(channel_id))
            if not channel:
                # Try fetching if not in cache
                channel = await self._client.fetch_channel(int(channel_id))

            if not channel:
                return f"Error: Discord channel {channel_id} not found."

            # Split long messages
            from inotagent.channels.discord import split_message
            for chunk in split_message(message):
                await channel.send(chunk)

            return f"Message sent to Discord channel {channel_id}."
        except Exception as e:
            logger.error(f"Discord send failed: {e}", exc_info=True)
            return f"Error sending to Discord: {e}"
