"""Channel protocol and shared types — all connectors implement this interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Protocol


@dataclass
class IncomingMessage:
    """Normalized message from any channel."""

    text: str
    sender_id: str
    sender_name: str
    conversation_id: str
    channel_type: str  # "discord", "slack", "whatsapp", "cli"
    raw: Any = None
    metadata: dict = field(default_factory=dict)


# Type alias for the message handler callback
MessageHandler = Callable[[IncomingMessage], Awaitable[str]]


class Channel(Protocol):
    """Interface for all communication channels.

    Channels are I/O connectors. They receive messages from external platforms,
    normalize them into IncomingMessage, feed them into the agent loop via the
    message handler, and send responses back to the platform.

    The agent loop doesn't know or care which channel a message came from.
    """

    async def start(self) -> None:
        """Connect to the platform and start listening."""
        ...

    async def stop(self) -> None:
        """Disconnect gracefully."""
        ...

    async def send(self, conversation_id: str, text: str) -> None:
        """Send a message to a conversation."""
        ...

    async def send_typing(self, conversation_id: str) -> None:
        """Show typing/activity indicator."""
        ...

    def set_message_handler(self, handler: MessageHandler) -> None:
        """Set the callback for incoming messages. Handler returns response text."""
        ...
