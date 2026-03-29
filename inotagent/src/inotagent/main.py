"""Entry point for inotagent — single-agent, multi-agent, CLI, and one-shot modes."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from pathlib import Path

from inotagent.channels import ChannelManager, IncomingMessage
from inotagent.channels.discord import DiscordChannel
from inotagent.channels.slack import SlackChannel
from inotagent.channels.telegram import TelegramChannel
from inotagent.config.agent import AgentConfig, load_agent_config
from inotagent.config.env import load_agent_env
from inotagent.config.models import load_models
from inotagent.config.platform import load_platform_config
from inotagent.llm.client import LLMMessage
from inotagent.loop import AgentLoop
from inotagent.tools.setup import create_tool_registry

logger = logging.getLogger(__name__)


# ---- Path resolution ----

def resolve_paths(agent_dir: str) -> tuple[Path, Path, Path]:
    """Resolve agent dir and find core config files."""
    agent_path = Path(agent_dir).resolve()
    if not agent_path.exists():
        raise FileNotFoundError(f"Agent directory not found: {agent_path}")

    repo_root = agent_path.parent.parent
    inotagent_dir = repo_root / "inotagent"
    if not inotagent_dir.exists():
        raise FileNotFoundError(f"inotagent directory not found at {inotagent_dir}")

    return agent_path, inotagent_dir / "models.yml", inotagent_dir / "platform.yml"


def resolve_agents_root(agent_dir: str) -> tuple[Path, Path, Path]:
    """Resolve from any agent dir to agents root + config paths."""
    agent_path = Path(agent_dir).resolve()
    agents_root = agent_path.parent
    repo_root = agents_root.parent
    inotagent_dir = repo_root / "inotagent"
    return agents_root, inotagent_dir / "models.yml", inotagent_dir / "platform.yml"


# ---- Shared infrastructure ----

async def try_init_db() -> bool:
    """Try to initialize the database pool. Returns True if successful."""
    try:
        from inotagent.db.pool import init_pool
        await init_pool()
        logger.info("Database pool initialized")
        return True
    except Exception as e:
        logger.warning(f"Database not available, running without persistence: {e}")
        return False


# ---- Channel setup ----

def setup_channels(
    config: AgentConfig,
    agent_loop: AgentLoop,
    agent_env: dict[str, str] | None = None,
    platform=None,
    models: dict | None = None,
) -> tuple[ChannelManager, DiscordChannel | None]:
    """Configure channels from agent config. Uses agent_env dict for tokens (multi-agent safe)."""
    channels = ChannelManager()
    discord_ch = None
    env = agent_env or {}

    def _get_env(key: str) -> str | None:
        """Get env var from agent-specific env first, then OS env."""
        return env.get(key) or os.environ.get(key)

    async def handle_message(msg: IncomingMessage) -> str:
        return await agent_loop.run(
            msg.text,
            conversation_id=msg.conversation_id,
            channel_type=msg.channel_type,
        )

    # Discord
    discord_config = config.channels.get("discord")
    if discord_config and discord_config.get("enabled"):
        token_env = discord_config.get("token_env", "DISCORD_BOT_TOKEN")
        token = _get_env(token_env)
        if token:
            discord_ch = DiscordChannel(token=token, config=discord_config)
            discord_ch.set_message_handler(handle_message)
            if platform and models:
                discord_ch.set_prompt_gen(platform.prompt_gen, models)
            channels.register("discord", discord_ch)
            logger.info(f"Discord channel configured (token_env={token_env})")
        else:
            logger.warning(f"Discord enabled but {token_env} not set, skipping")

    # Slack
    slack_config = config.channels.get("slack")
    if slack_config and slack_config.get("enabled"):
        bot_token_env = slack_config.get("bot_token_env", "SLACK_BOT_TOKEN")
        app_token_env = slack_config.get("app_token_env", "SLACK_APP_TOKEN")
        bot_token = _get_env(bot_token_env)
        app_token = _get_env(app_token_env)
        if bot_token and app_token:
            slack_ch = SlackChannel(bot_token=bot_token, app_token=app_token, config=slack_config)
            slack_ch.set_message_handler(handle_message)
            channels.register("slack", slack_ch)
            logger.info(f"Slack channel configured (bot_token_env={bot_token_env})")
        else:
            missing = [k for k, v in {bot_token_env: bot_token, app_token_env: app_token}.items() if not v]
            logger.warning(f"Slack enabled but {', '.join(missing)} not set, skipping")

    # Telegram
    telegram_config = config.channels.get("telegram")
    if telegram_config and telegram_config.get("enabled"):
        token_env = telegram_config.get("token_env", "TELEGRAM_BOT_TOKEN")
        token = _get_env(token_env)
        if token:
            telegram_ch = TelegramChannel(token=token, config=telegram_config)
            telegram_ch.set_message_handler(handle_message)
            channels.register("telegram", telegram_ch)
            logger.info(f"Telegram channel configured (token_env={token_env})")
        else:
            logger.warning(f"Telegram enabled but {token_env} not set, skipping")

    return channels, discord_ch


# ---- Per-agent initialization ----

async def init_agent(
    agent_path: Path,
    models: dict,
    platform,
    db_available: bool,
    agent_env: dict[str, str] | None = None,
) -> tuple[AgentLoop, ChannelManager, DiscordChannel | None, object | None]:
    """Initialize a single agent: config, tools, loop, heartbeat, channels."""
    # Inject agent env vars into os.environ (LLM clients read from there)
    if agent_env:
        for k, v in agent_env.items():
            if v:
                os.environ[k] = v

    # Set AGENT_NAME to individual agent (not the comma-separated AGENTS list)
    os.environ["AGENT_NAME"] = agent_path.name

    config = load_agent_config(agent_path, models, platform)

    # Load DB overrides and skills
    if db_available:
        try:
            await config.refresh_from_db(models)
        except Exception as e:
            logger.warning(f"[{config.name}] Failed to load DB configs: {e}")
        try:
            await config.refresh_skills()
            logger.info(f"Loaded {len(config._skill_ids)} skill(s): {config._skill_names}")
        except Exception as e:
            logger.warning(f"[{config.name}] Failed to load skills: {e}")

        # Store system prompt token count
        try:
            from inotagent.db.agent_configs import upsert_agent_config
            from inotagent.llm.tokens import count_tokens
            prompt_tokens = count_tokens(config.system_prompt_with_skills, config.model_id)
            await upsert_agent_config(
                config.name, "system_prompt_tokens", str(prompt_tokens),
                "Estimated token count of system prompt (AGENTS.md + TOOLS.md + skills)",
            )
            logger.info(f"System prompt: ~{prompt_tokens} tokens")
        except Exception as e:
            logger.warning(f"[{config.name}] Failed to store prompt token count: {e}")

    # Workspace: per-agent subdirectory in multi-agent mode
    default_workspace = os.environ.get("WORKSPACE_DIR", str(agent_path))
    workspace_dir = os.path.join(default_workspace, config.name) if os.environ.get("AGENTS") else default_workspace

    tool_registry = create_tool_registry(
        agent_name=config.name,
        default_working_dir=workspace_dir,
        db_available=db_available,
        models=models,
        config=config,
    )

    agent_loop = AgentLoop(
        config=config,
        models=models,
        tool_registry=tool_registry,
        db_available=db_available,
    )

    logger.info(
        f"Agent '{config.name}' initialized with model '{config.model_id}' "
        f"({len(tool_registry.get_definitions())} tools, db={'yes' if db_available else 'no'})"
    )

    # Start heartbeat
    heartbeat = None
    if db_available:
        from inotagent.scheduler.heartbeat import Heartbeat
        heartbeat = Heartbeat(agent_name=config.name, agent_loop=agent_loop, mission_tags=config.mission_tags)
        await heartbeat.start()

    # Setup channels
    channels, discord_ch = setup_channels(
        config, agent_loop, agent_env=agent_env, platform=platform, models=models,
    )

    # Inject Discord client into discord_send tool
    if discord_ch and hasattr(tool_registry, "_discord_send_tool"):
        async def _inject(dc=discord_ch, tr=tool_registry):
            while not dc._client or not dc._client.is_ready():
                await asyncio.sleep(0.5)
            tr._discord_send_tool.set_client(dc._client)
        asyncio.create_task(_inject())

    return agent_loop, channels, discord_ch, heartbeat


# ---- CLI mode ----

async def cli_mode(agent_loop: AgentLoop) -> None:
    """Interactive CLI for testing the agent loop."""
    print(f"inotagent [{agent_loop.config.name}] ready.")
    print(f"  Model: {agent_loop.config.model_id}")
    print(f"  Fallbacks: {agent_loop.config.fallbacks or 'none'}")
    print(f"  DB: {'connected' if agent_loop.db_available else 'not connected'}")
    print("Type messages, Ctrl+C to exit.\n")

    conv_id = f"cli-{agent_loop.config.name}" if agent_loop.db_available else None
    history: list[LLMMessage] = []

    while True:
        try:
            user_input = await asyncio.get_event_loop().run_in_executor(None, lambda: input("> "))
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user_input.strip():
            continue

        try:
            response = await agent_loop.run(
                user_input,
                history=history if not conv_id else None,
                conversation_id=conv_id,
                channel_type="cli",
            )
            print(f"\n{response}\n")
            if not conv_id:
                history.append(LLMMessage(role="user", content=user_input))
                history.append(LLMMessage(role="assistant", content=response))
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            print(f"\nError: {e}\n")


# ---- Main entry points ----

async def async_main_single(args: argparse.Namespace) -> None:
    """Single-agent mode (backward compatible): --agent-dir /app/agents/robin"""
    agent_path, models_path, platform_path = resolve_paths(args.agent_dir)

    models = load_models(models_path)
    platform = load_platform_config(platform_path)

    # Shared infrastructure
    from inotagent.llm.embeddings import init_embedding_client
    if init_embedding_client(platform.embedding):
        logger.info("Semantic memory search enabled")

    db_available = await try_init_db()

    # Load agent env (for multi-agent compatibility — also works in single mode)
    agent_env = load_agent_env(agent_path / ".env")

    # One-shot mode
    if args.message:
        config = load_agent_config(agent_path, models, platform)
        workspace_dir = os.environ.get("WORKSPACE_DIR", str(agent_path))
        tool_registry = create_tool_registry(agent_name=config.name, default_working_dir=workspace_dir, db_available=db_available)
        loop = AgentLoop(config=config, models=models, tool_registry=tool_registry, db_available=db_available)
        response = await loop.run(args.message)
        print(response)
        return

    agent_loop, channels, discord_ch, heartbeat = await init_agent(
        agent_path, models, platform, db_available, agent_env=agent_env,
    )

    try:
        if channels.has_channels():
            logger.info("Starting in channel mode")
            await channels.start_all()
        else:
            logger.info("No channels configured, starting CLI mode")
            await cli_mode(agent_loop)
    finally:
        if heartbeat:
            await heartbeat.stop()
        await channels.stop_all()
        if db_available:
            from inotagent.db.pool import close_pool
            await close_pool()


async def async_main_multi(args: argparse.Namespace) -> None:
    """Multi-agent mode: --agents ino,robin or AGENTS=ino,robin env var."""
    agent_names = [n.strip() for n in args.agents.split(",") if n.strip()]
    if not agent_names:
        logger.error("No agents specified")
        return

    # Resolve paths from first agent dir
    agents_root = Path(args.agents_root).resolve() if args.agents_root else Path("/app/agents")
    first_agent = agents_root / agent_names[0]
    if not first_agent.exists():
        # Try relative to CWD
        agents_root = Path.cwd() / "agents"
        first_agent = agents_root / agent_names[0]

    repo_root = agents_root.parent
    inotagent_dir = repo_root / "inotagent"
    models_path = inotagent_dir / "models.yml"
    platform_path = inotagent_dir / "platform.yml"

    models = load_models(models_path)
    platform = load_platform_config(platform_path)

    db_available = await try_init_db()

    # Load first agent's env to get API keys before initializing embedding client
    first_env = load_agent_env(agents_root / agent_names[0] / ".env")
    for k, v in first_env.items():
        if v:
            os.environ[k] = v

    from inotagent.llm.embeddings import init_embedding_client
    if init_embedding_client(platform.embedding):
        logger.info("Semantic memory search enabled")

    # Initialize all agents
    runners: list[tuple[str, AgentLoop, ChannelManager, object | None]] = []
    for name in agent_names:
        agent_path = agents_root / name
        if not agent_path.exists():
            logger.error(f"Agent directory not found: {agent_path}, skipping")
            continue

        agent_env = load_agent_env(agent_path / ".env")

        try:
            agent_loop, channels, discord_ch, heartbeat = await init_agent(
                agent_path, models, platform, db_available, agent_env=agent_env,
            )
            runners.append((name, agent_loop, channels, heartbeat))
            logger.info(f"Agent '{name}' ready")
        except Exception as e:
            logger.error(f"Failed to initialize agent '{name}': {e}", exc_info=True)

    if not runners:
        logger.error("No agents initialized, exiting")
        return

    logger.info(f"Starting {len(runners)} agent(s): {[r[0] for r in runners]}")

    # Start all channel managers concurrently
    async def run_agent(name: str, channels: ChannelManager):
        try:
            if channels.has_channels():
                await channels.start_all()
            else:
                logger.info(f"[{name}] No channels configured, idle")
                while True:
                    await asyncio.sleep(3600)
        except Exception as e:
            logger.error(f"[{name}] Agent crashed: {e}", exc_info=True)

    try:
        await asyncio.gather(
            *[run_agent(name, channels) for name, _, channels, _ in runners]
        )
    finally:
        for name, _, channels, heartbeat in runners:
            if heartbeat:
                await heartbeat.stop()
            await channels.stop_all()
        if db_available:
            from inotagent.db.pool import close_pool
            await close_pool()


async def async_main(args: argparse.Namespace) -> None:
    """Route to single or multi-agent mode."""
    # Multi-agent: --agents flag or AGENTS env var
    agents = args.agents or os.environ.get("AGENTS", "")
    if agents:
        args.agents = agents
        await async_main_multi(args)
    elif args.agent_dir:
        await async_main_single(args)
    else:
        logger.error("Specify --agent-dir (single) or --agents (multi)")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="inotagent — async agent runtime")
    parser.add_argument(
        "--agent-dir",
        help="Path to agent directory (single-agent mode, e.g., agents/robin)",
    )
    parser.add_argument(
        "--agents",
        help="Comma-separated agent names (multi-agent mode, e.g., ino,robin)",
    )
    parser.add_argument(
        "--agents-root",
        help="Path to agents directory (default: /app/agents or ./agents)",
    )
    parser.add_argument(
        "-m", "--message",
        help="Send a single message and exit (single-agent only)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
