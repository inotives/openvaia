"""Tool registry — register tools and dispatch execution."""

from __future__ import annotations

import logging
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)

# A tool handler takes keyword arguments and returns a string result.
ToolHandler = Callable[..., Awaitable[str]]


class ToolRegistry:
    """Registry for agent tools — stores definitions and handlers."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolHandler] = {}
        self._definitions: dict[str, dict] = {}

    def register(self, name: str, handler: ToolHandler, definition: dict) -> None:
        """Register a tool with its async handler and Anthropic-format schema."""
        self._tools[name] = handler
        self._definitions[name] = definition
        logger.debug(f"Tool registered: {name}")

    def get_definitions(self) -> list[dict]:
        """Return all tool definitions in Anthropic format (for LLM prompt)."""
        return list(self._definitions.values())

    def has_tools(self) -> bool:
        return len(self._tools) > 0

    async def execute(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool call by name. Returns result string or error message."""
        handler = self._tools.get(name)
        if not handler:
            return f"Error: Unknown tool '{name}'. Available tools: {list(self._tools.keys())}"

        try:
            return await handler(**arguments)
        except Exception as e:
            logger.error(f"Tool '{name}' failed: {e}", exc_info=True)
            return f"Error executing tool '{name}': {e}"
