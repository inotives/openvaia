"""Channel abstraction layer — start/stop all configured channels."""

from __future__ import annotations

import asyncio
import logging

from inotagent.channels.base import Channel, IncomingMessage, MessageHandler

logger = logging.getLogger(__name__)

__all__ = [
    "Channel",
    "ChannelManager",
    "IncomingMessage",
    "MessageHandler",
]


class ChannelManager:
    """Manages all registered channel connectors."""

    def __init__(self) -> None:
        self._channels: dict[str, Channel] = {}

    def register(self, name: str, channel: Channel) -> None:
        self._channels[name] = channel
        logger.info(f"Channel registered: {name}")

    def has_channels(self) -> bool:
        return len(self._channels) > 0

    async def start_all(self) -> None:
        """Start all registered channels concurrently."""
        if not self._channels:
            return
        logger.info(f"Starting {len(self._channels)} channel(s): {list(self._channels.keys())}")
        await asyncio.gather(*[ch.start() for ch in self._channels.values()])

    async def stop_all(self) -> None:
        """Stop all channels gracefully."""
        for name, ch in self._channels.items():
            try:
                await ch.stop()
                logger.info(f"Channel stopped: {name}")
            except Exception as e:
                logger.error(f"Error stopping channel {name}: {e}")
