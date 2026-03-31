"""Wire up all tools into a ToolRegistry for an agent."""

from __future__ import annotations

from inotagent.tools.browser import BROWSER_TOOL, BrowserTool
from inotagent.tools.discord_tool import DISCORD_SEND_TOOL, DiscordSendTool
from inotagent.tools.files import FILE_TOOLS, list_files, read_file, search_files
from inotagent.tools.memory import MEMORY_TOOLS, MemoryTools
from inotagent.tools.platform import PLATFORM_TOOLS, PlatformTools
from inotagent.tools.registry import ToolRegistry
from inotagent.tools.research import RESEARCH_TOOLS, ResearchTools
from inotagent.tools.shell import SHELL_TOOL, execute as shell_execute


def create_tool_registry(
    agent_name: str,
    default_working_dir: str | None = None,
    db_available: bool = False,
    models: dict | None = None,
    config=None,
) -> ToolRegistry:
    """Create a ToolRegistry with all standard agent tools.

    Returns (registry, discord_send_tool) — caller must inject Discord client
    into discord_send_tool after channel setup via discord_send_tool.set_client().
    """
    registry = ToolRegistry()

    # Shell
    registry.register("shell", shell_execute, SHELL_TOOL)

    # File tools
    registry.register("read_file", read_file, FILE_TOOLS[0])
    registry.register("list_files", list_files, FILE_TOOLS[1])
    registry.register("search_files", search_files, FILE_TOOLS[2])

    # Browser (lazy-loaded)
    browser = BrowserTool()
    registry.register("browser", browser.execute, BROWSER_TOOL)

    # Discord send (client injected later)
    discord_send = DiscordSendTool()
    registry.register("discord_send", discord_send.execute, DISCORD_SEND_TOOL)

    # Platform tools (DB-backed when available)
    platform = PlatformTools(agent_name=agent_name, db_available=db_available)
    registry.register("task_list", platform.task_list, PLATFORM_TOOLS[0])
    registry.register("task_update", platform.task_update, PLATFORM_TOOLS[1])
    registry.register("task_create", platform.task_create, PLATFORM_TOOLS[2])
    registry.register("send_message", platform.send_message, PLATFORM_TOOLS[3])
    registry.register("skill_create", platform.skill_create, PLATFORM_TOOLS[4])
    registry.register("skill_propose", platform.skill_propose, PLATFORM_TOOLS[5])

    # Resource tools (DB-backed when available)
    from inotagent.tools.resources import RESOURCE_TOOLS, ResourceTools
    resources = ResourceTools(agent_name=agent_name, db_available=db_available)
    registry.register("resource_search", resources.resource_search, RESOURCE_TOOLS[0])
    registry.register("resource_add", resources.resource_add, RESOURCE_TOOLS[1])

    # Email tool
    from inotagent.tools.email import EmailTool, SEND_EMAIL_TOOL
    email_tool = EmailTool(agent_name=agent_name)
    registry.register("send_email", email_tool.send_email, SEND_EMAIL_TOOL)

    # Memory tools (DB-backed when available)
    memory = MemoryTools(agent_name=agent_name, db_available=db_available)
    registry.register("memory_store", memory.memory_store, MEMORY_TOOLS[0])
    registry.register("memory_search", memory.memory_search, MEMORY_TOOLS[1])

    # Research tools (DB-backed when available)
    research = ResearchTools(agent_name=agent_name, db_available=db_available)
    registry.register("research_store", research.research_store, RESEARCH_TOOLS[0])
    registry.register("research_search", research.research_search, RESEARCH_TOOLS[1])
    registry.register("research_get", research.research_get, RESEARCH_TOOLS[2])

    # Delegate tool (sub-agents — requires models + config)
    if models and config:
        from inotagent.tools.delegate import DelegateTool, DELEGATE_TOOL
        delegate = DelegateTool(agent_name=agent_name, models=models, config=config, db_available=db_available)
        registry.register("delegate", delegate.delegate, DELEGATE_TOOL)

    # Attach discord_send ref for client injection
    registry._discord_send_tool = discord_send  # type: ignore[attr-defined]

    return registry
