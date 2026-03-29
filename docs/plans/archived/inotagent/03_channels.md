# Phase 3: Channels

**Goal**: Build a channel abstraction layer and implement the first connector (Discord). Future connectors (Slack, WhatsApp, Telegram) plug in using the same interface.

**Delivers**: Agent communicates via Discord. Adding a new channel is just implementing a `Channel` class — no changes to agent loop, tools, or persistence.

**Complexity**: Medium

## Dependencies

- Phase 1 (Foundation) — agent loop, config
- Phase 2 (Tool System) — tool execution

## Design principle

Channels are just I/O connectors. They receive messages from external platforms and feed them into the agent loop. They take agent responses and send them back. The agent loop doesn't know or care which channel a message came from.

```
External Platform  ←→  Channel Connector  ←→  Agent Loop
(Discord, Slack...)    (implements Channel)     (LLM + tools)
```

## What to build

### 3.1 Channel protocol (`channels/base.py`)

Abstract interface all connectors implement:

```python
from dataclasses import dataclass
from typing import Protocol, Callable, Awaitable, Any

@dataclass
class IncomingMessage:
    """Normalized message from any channel."""
    text: str                          # message content
    sender_id: str                     # platform-specific user ID
    sender_name: str                   # display name
    conversation_id: str               # maps to agent loop conversation
    channel_type: str                  # "discord", "slack", "whatsapp"
    raw: Any                           # original platform message object
    metadata: dict | None = None       # platform-specific extras

class Channel(Protocol):
    """Interface for all communication channels."""

    async def start(self) -> None:
        """Connect to the platform and start listening."""
        ...

    async def stop(self) -> None:
        """Disconnect gracefully."""
        ...

    async def send(self, conversation_id: str, text: str) -> None:
        """Send a message back to a conversation."""
        ...

    async def send_typing(self, conversation_id: str) -> None:
        """Show typing/activity indicator."""
        ...

    def set_message_handler(self, handler: Callable[[IncomingMessage], Awaitable[str]]) -> None:
        """Set the callback for incoming messages. Handler returns response text."""
        ...
```

Every connector normalizes platform-specific messages into `IncomingMessage` and sends responses as plain text. Platform-specific formatting (embeds, buttons, etc.) stays inside the connector.

### 3.2 Channel manager (`channels/__init__.py`)

Start/stop all configured channels:

```python
class ChannelManager:
    def __init__(self):
        self._channels: dict[str, Channel] = {}

    def register(self, name: str, channel: Channel):
        self._channels[name] = channel

    def has_channels(self) -> bool:
        return len(self._channels) > 0

    async def start_all(self):
        """Start all registered channels concurrently."""
        await asyncio.gather(*[ch.start() for ch in self._channels.values()])

    async def stop_all(self):
        for ch in self._channels.values():
            await ch.stop()
```

### 3.3 Discord connector (`channels/discord.py`)

First implementation of the Channel protocol:

```python
import discord

class DiscordChannel:
    """Discord connector implementing the Channel protocol."""

    def __init__(self, token: str, config: dict):
        self.token = token
        self.config = config             # guilds, allowFrom, requireMention
        self._handler = None
        self._client: discord.Client | None = None
        self._conversations: dict[str, discord.abc.Messageable] = {}

    def set_message_handler(self, handler):
        self._handler = handler

    async def start(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.dm_messages = True
        self._client = discord.Client(intents=intents)

        @self._client.event
        async def on_ready():
            logger.info(f"Discord connected: {self._client.user.name}")

        @self._client.event
        async def on_message(message: discord.Message):
            if message.author.bot:
                return
            if not self._should_respond(message):
                return
            await self._handle_message(message)

        await self._client.start(self.token)

    async def stop(self):
        if self._client:
            await self._client.close()

    async def send(self, conversation_id: str, text: str):
        target = self._conversations.get(conversation_id)
        if not target:
            return
        for chunk in _split_message(text):
            await target.send(chunk)

    async def send_typing(self, conversation_id: str):
        target = self._conversations.get(conversation_id)
        if target:
            await target.typing()

    async def _handle_message(self, message: discord.Message):
        conversation_id = self._get_conversation_id(message)
        self._conversations[conversation_id] = message.channel

        incoming = IncomingMessage(
            text=message.content,
            sender_id=str(message.author.id),
            sender_name=message.author.display_name,
            conversation_id=conversation_id,
            channel_type="discord",
            raw=message,
        )

        async with message.channel.typing():
            response = await self._handler(incoming)

        for chunk in _split_message(response):
            await message.channel.send(chunk, reference=message)

    def _should_respond(self, message: discord.Message) -> bool:
        if isinstance(message.channel, discord.DMChannel):
            return self._is_allowed_user(message.author.id)

        guild_config = self.config.get("guilds", {}).get(str(message.guild.id))
        if not guild_config:
            return False
        if guild_config.get("requireMention", True):
            return self._client.user.mentioned_in(message)
        return True

    def _is_allowed_user(self, user_id: int) -> bool:
        allow_from = self.config.get("allowFrom", [])
        if not allow_from:
            return True
        return str(user_id) in allow_from

    def _get_conversation_id(self, message: discord.Message) -> str:
        if isinstance(message.channel, discord.Thread):
            return f"discord-thread-{message.channel.id}"
        if isinstance(message.channel, discord.DMChannel):
            return f"discord-dm-{message.author.id}"
        return f"discord-channel-{message.channel.id}"


def _split_message(text: str, max_len: int = 2000) -> list[str]:
    """Split long text at newlines or spaces to fit platform limits."""
    if len(text) <= max_len:
        return [text]
    chunks = []
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
```

### 3.4 Future connectors (stubs)

These show how new connectors plug in with zero changes to the agent loop:

**Slack** (`channels/slack.py` — future):
```python
class SlackChannel:
    """Slack connector using slack-sdk. Implements Channel protocol."""
    # Uses slack_sdk.web.async_client.AsyncWebClient
    # Socket Mode for real-time events
    # Message limit: 4000 chars (vs Discord's 2000)
    # Same interface: start, stop, send, send_typing, set_message_handler
```

**WhatsApp** (`channels/whatsapp.py` — future):
```python
class WhatsAppChannel:
    """WhatsApp connector via WhatsApp Business API. Implements Channel protocol."""
    # Webhook-based: receive messages via HTTP POST
    # Send via WhatsApp Cloud API
    # Message limit: 4096 chars
    # Same interface
```

**Telegram** (`channels/telegram.py` — future):
```python
class TelegramChannel:
    """Telegram connector using python-telegram-bot. Implements Channel protocol."""
    # Long-polling or webhook
    # Message limit: 4096 chars
    # Same interface
```

### 3.5 Entry point integration (`main.py`)

Wire channels into startup. Token env var comes from YAML, everything else from DB:

```python
async def main():
    config = load_agent_config(...)
    loop = AgentLoop(config, llm, models, tools)

    async def handle_message(msg: IncomingMessage) -> str:
        return await loop.run(msg.text, msg.conversation_id, channel_type=msg.channel_type)

    channels = ChannelManager()

    # Discord: check if token_env is configured in YAML, then load settings from DB
    if discord_yaml := config.channels.get("discord"):
        discord_db = await load_channel_config(config.name, "discord")
        if discord_db.get("enabled") == "true":
            ch = DiscordChannel(
                token=os.environ[discord_yaml["token_env"]],
                config=discord_db,          # from DB, not YAML
            )
            ch.set_message_handler(handle_message)
            channels.register("discord", ch)

    # Future:
    # if slack_yaml := config.channels.get("slack"):
    #     slack_db = await load_channel_config(config.name, "slack")
    #     if slack_db.get("enabled") == "true":
    #         ch = SlackChannel(token=os.environ[slack_yaml["token_env"]], config=slack_db)
    #         ...

    if channels.has_channels():
        await channels.start_all()
    else:
        await cli_mode(loop)
```

### 3.6 Config: DB-first, YAML-minimal

Channel config lives in `platform.config` table so changes don't require redeploy. YAML only holds what can't go in DB (env var names for secrets).

**agent.yml** — static only:
```yaml
# agents/robin/agent.yml
model: nvidia-minimax-2.5
parallel: false

channels:
  discord:
    token_env: DISCORD_BOT_TOKEN      # which env var holds the token (secret, never in DB)
  # slack:
  #   token_env: SLACK_BOT_TOKEN
  # whatsapp:
  #   token_env: WHATSAPP_API_TOKEN
```

**platform.config** — runtime-configurable:
```sql
-- Discord config for robin
INSERT INTO config (key, value, description) VALUES
  ('channels.discord.robin.enabled',        'true',             'Enable Discord for robin'),
  ('channels.discord.robin.allowFrom',      '207679848406056960', 'Comma-separated user IDs allowed to DM'),
  ('channels.discord.robin.guilds',         '{"1474374113597456425": {"requireMention": true}}', 'Guild-specific settings (JSON)'),

-- Discord config for ino
  ('channels.discord.ino.enabled',          'true',             'Enable Discord for ino'),
  ('channels.discord.ino.allowFrom',        '207679848406056960', 'Comma-separated user IDs allowed to DM'),
  ('channels.discord.ino.guilds',           '{"1474374113597456425": {"requireMention": true}}', 'Guild-specific settings (JSON)'),

-- Global defaults (applied if no agent-specific key)
  ('channels.discord.enabled',              'true',             'Default: enable Discord for all agents'),
  ('channels.discord.allowFrom',            '',                 'Default: no DM restriction'),
  ('channels.discord.guilds',               '{}',               'Default: no guild config');
```

**Config resolution** (agent-specific → global → default):
```python
async def load_channel_config(agent_name: str, channel_type: str) -> dict:
    """Load channel config from DB with fallback chain.

    Resolution: channels.{type}.{agent}.{key} → channels.{type}.{key} → default
    """
    async with get_connection() as conn:
        rows = await conn.execute(
            f"SELECT key, value FROM {SCHEMA}.config WHERE key LIKE 'channels.{channel_type}.%%'"
        ).fetchall()

    config = {}
    for row in rows:
        parts = row["key"].split(".")
        # channels.discord.robin.enabled → agent-specific
        # channels.discord.enabled → global default
        if len(parts) == 4 and parts[2] == agent_name:
            config[parts[3]] = row["value"]
        elif len(parts) == 3 and parts[2] not in config:
            # Global default, only if no agent-specific override
            config[parts[2]] = row["value"]

    # Parse JSON fields
    if "guilds" in config:
        config["guilds"] = json.loads(config["guilds"])
    if "allowFrom" in config:
        config["allowFrom"] = [x.strip() for x in config["allowFrom"].split(",") if x.strip()]

    return config
```

**Runtime changes without redeploy:**
```sql
-- Add a new allowed user
UPDATE config SET value = '207679848406056960,123456789012345678'
WHERE key = 'channels.discord.robin.allowFrom';

-- Add a new guild
UPDATE config SET value = '{"1474374113597456425": {"requireMention": true}, "9876543210": {"requireMention": false}}'
WHERE key = 'channels.discord.robin.guilds';

-- Disable Discord for robin
UPDATE config SET value = 'false'
WHERE key = 'channels.discord.robin.enabled';
```

Channels pick up config changes via heartbeat config reload (Phase 5) — no restart needed.

**Future channels follow the same pattern:**
```sql
-- Enable Slack for robin
INSERT INTO config (key, value) VALUES
  ('channels.slack.robin.enabled',    'true'),
  ('channels.slack.robin.channels',   'C0123456789,C9876543210');
```

## Files to create/modify

| File | Action |
|------|--------|
| `src/inotagent/channels/__init__.py` | Create — ChannelManager |
| `src/inotagent/channels/base.py` | Create — Channel protocol + IncomingMessage |
| `src/inotagent/channels/discord.py` | Create — Discord connector |
| `src/inotagent/main.py` | Modify — wire channels into startup |
| `tests/test_channels.py` | Create — message filtering, chunking, protocol tests |

## Existing code reference

- `core/platform.yml` channels section — default config format
- `agents/*/agent.yml` channels section — per-agent overrides

## How to verify

1. Set `DISCORD_BOT_TOKEN` → start agent → bot comes online in Discord
2. DM the bot → get a response from the LLM
3. @mention in guild → bot responds
4. Long response (>2000 chars) → properly chunked
5. Non-allowed user → ignored
6. No channels configured → falls back to CLI mode
7. `DiscordChannel` satisfies `Channel` protocol (static type check)
