"""Tests for channels — base protocol, Discord connector, Slack connector, channel manager."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from inotagent.channels import ChannelManager, IncomingMessage
from inotagent.channels.base import Channel
from inotagent.channels.discord import DiscordChannel, split_message, _get_conversation_id
from inotagent.channels.slack import SlackChannel
from inotagent.channels.slack import split_message as slack_split_message
from inotagent.channels.slack import _get_conversation_id as slack_get_conversation_id
from inotagent.channels.telegram import TelegramChannel
from inotagent.channels.telegram import split_message as telegram_split_message
from inotagent.channels.telegram import _get_conversation_id as telegram_get_conversation_id


# --- IncomingMessage tests ---


class TestIncomingMessage:
    def test_create_message(self):
        msg = IncomingMessage(
            text="hello",
            sender_id="123",
            sender_name="toni",
            conversation_id="discord-dm-123",
            channel_type="discord",
        )
        assert msg.text == "hello"
        assert msg.sender_id == "123"
        assert msg.channel_type == "discord"
        assert msg.raw is None
        assert msg.metadata == {}

    def test_message_with_metadata(self):
        msg = IncomingMessage(
            text="hi",
            sender_id="123",
            sender_name="toni",
            conversation_id="discord-channel-456",
            channel_type="discord",
            metadata={"guild_id": "789"},
        )
        assert msg.metadata["guild_id"] == "789"


# --- ChannelManager tests ---


class TestChannelManager:
    def test_has_channels_empty(self):
        manager = ChannelManager()
        assert manager.has_channels() is False

    def test_has_channels_with_registration(self):
        manager = ChannelManager()
        mock_channel = MagicMock()
        manager.register("discord", mock_channel)
        assert manager.has_channels() is True

    async def test_start_all(self):
        manager = ChannelManager()
        ch1 = AsyncMock()
        ch2 = AsyncMock()
        manager.register("discord", ch1)
        manager.register("slack", ch2)

        await manager.start_all()

        ch1.start.assert_awaited_once()
        ch2.start.assert_awaited_once()

    async def test_stop_all(self):
        manager = ChannelManager()
        ch1 = AsyncMock()
        ch2 = AsyncMock()
        manager.register("discord", ch1)
        manager.register("slack", ch2)

        await manager.stop_all()

        ch1.stop.assert_awaited_once()
        ch2.stop.assert_awaited_once()

    async def test_start_all_empty(self):
        manager = ChannelManager()
        await manager.start_all()  # should not raise

    async def test_stop_all_handles_errors(self):
        manager = ChannelManager()
        ch = AsyncMock()
        ch.stop.side_effect = Exception("disconnect failed")
        manager.register("discord", ch)

        await manager.stop_all()  # should not raise


# --- split_message tests ---


class TestSplitMessage:
    def test_short_message(self):
        assert split_message("hello") == ["hello"]

    def test_empty_message(self):
        assert split_message("") == [""]

    def test_exact_limit(self):
        text = "a" * 2000
        assert split_message(text) == [text]

    def test_split_at_newline(self):
        text = "a" * 1500 + "\n" + "b" * 1000
        chunks = split_message(text, max_len=2000)
        assert len(chunks) == 2
        assert chunks[0] == "a" * 1500
        assert chunks[1] == "b" * 1000

    def test_split_at_space(self):
        text = "word " * 500  # 2500 chars
        chunks = split_message(text, max_len=2000)
        assert len(chunks) == 2
        for chunk in chunks:
            assert len(chunk) <= 2000

    def test_hard_cut_no_whitespace(self):
        text = "a" * 3000
        chunks = split_message(text, max_len=2000)
        assert len(chunks) == 2
        assert chunks[0] == "a" * 2000
        assert chunks[1] == "a" * 1000

    def test_multiple_chunks(self):
        text = "a" * 5000
        chunks = split_message(text, max_len=2000)
        assert len(chunks) == 3
        assert "".join(chunks) == text

    def test_custom_max_len(self):
        text = "hello world foo bar"
        chunks = split_message(text, max_len=11)
        assert all(len(c) <= 11 for c in chunks)

    def test_preserves_content(self):
        text = "Line 1\nLine 2\nLine 3\nLine 4"
        chunks = split_message(text, max_len=15)
        reassembled = "\n".join(chunks)
        # All original lines should be present
        assert "Line 1" in reassembled
        assert "Line 4" in reassembled


# --- Discord conversation ID tests ---


class TestGetConversationId:
    def test_dm_channel(self):
        msg = MagicMock()
        msg.channel = MagicMock(spec=["id"])
        msg.channel.__class__ = type("DMChannel", (), {})
        msg.author.id = 12345

        # Manually simulate DMChannel isinstance check
        import discord
        msg.channel = MagicMock(spec=discord.DMChannel)
        msg.channel.id = 99999
        result = _get_conversation_id(msg)
        assert result == "discord-dm-12345"

    def test_thread_channel(self):
        import discord
        msg = MagicMock()
        msg.channel = MagicMock(spec=discord.Thread)
        msg.channel.id = 77777
        result = _get_conversation_id(msg)
        assert result == "discord-thread-77777"

    def test_guild_channel(self):
        import discord
        msg = MagicMock()
        # Regular text channel — not a DMChannel or Thread
        msg.channel = MagicMock(spec=discord.TextChannel)
        msg.channel.id = 55555
        result = _get_conversation_id(msg)
        assert result == "discord-channel-55555"


# --- Discord _should_respond tests ---


class TestShouldRespond:
    @pytest.fixture
    def discord_channel(self):
        ch = DiscordChannel(token="fake-token", config={
            "enabled": True,
            "allowFrom": ["207679848406056960"],
            "guilds": {
                "1474374113597456425": {"requireMention": True},
                "9999999999999999999": {"requireMention": False},
            },
        })
        ch._client = MagicMock()
        ch._client.user = MagicMock()
        ch._client.user.id = 111111
        return ch

    def test_dm_allowed_user(self, discord_channel):
        import discord
        msg = MagicMock()
        msg.channel = MagicMock(spec=discord.DMChannel)
        msg.author.id = 207679848406056960
        assert discord_channel._should_respond(msg) is True

    def test_dm_disallowed_user(self, discord_channel):
        import discord
        msg = MagicMock()
        msg.channel = MagicMock(spec=discord.DMChannel)
        msg.author.id = 999999999
        assert discord_channel._should_respond(msg) is False

    def test_dm_no_allow_list(self):
        ch = DiscordChannel(token="fake", config={"enabled": True, "allowFrom": []})
        ch._client = MagicMock()

        import discord
        msg = MagicMock()
        msg.channel = MagicMock(spec=discord.DMChannel)
        msg.author.id = 12345
        assert ch._should_respond(msg) is True  # no restriction

    def test_guild_with_mention_required_and_mentioned(self, discord_channel):
        import discord
        msg = MagicMock()
        msg.channel = MagicMock(spec=discord.TextChannel)
        msg.guild = MagicMock()
        msg.guild.id = 1474374113597456425
        discord_channel._client.user.mentioned_in.return_value = True
        assert discord_channel._should_respond(msg) is True

    def test_guild_with_mention_required_not_mentioned(self, discord_channel):
        import discord
        msg = MagicMock()
        msg.channel = MagicMock(spec=discord.TextChannel)
        msg.guild = MagicMock()
        msg.guild.id = 1474374113597456425
        discord_channel._client.user.mentioned_in.return_value = False
        assert discord_channel._should_respond(msg) is False

    def test_guild_without_mention_required(self, discord_channel):
        import discord
        msg = MagicMock()
        msg.channel = MagicMock(spec=discord.TextChannel)
        msg.guild = MagicMock()
        msg.guild.id = 9999999999999999999  # requireMention: False
        assert discord_channel._should_respond(msg) is True

    def test_unknown_guild(self, discord_channel):
        import discord
        msg = MagicMock()
        msg.channel = MagicMock(spec=discord.TextChannel)
        msg.guild = MagicMock()
        msg.guild.id = 1111111111111111111  # not in config
        assert discord_channel._should_respond(msg) is False

    def test_no_guild(self, discord_channel):
        import discord
        msg = MagicMock()
        msg.channel = MagicMock(spec=discord.TextChannel)
        msg.guild = None
        assert discord_channel._should_respond(msg) is False


# --- Discord handler and set_message_handler tests ---


class TestDiscordChannel:
    def test_set_message_handler(self):
        ch = DiscordChannel(token="fake", config={})
        handler = AsyncMock()
        ch.set_message_handler(handler)
        assert ch._handler is handler

    async def test_send_no_target(self):
        ch = DiscordChannel(token="fake", config={})
        # Should not raise even with unknown conversation
        await ch.send("unknown-conv", "hello")

    async def test_send_to_known_target(self):
        ch = DiscordChannel(token="fake", config={})
        mock_target = AsyncMock()
        ch._conversations["conv-1"] = mock_target

        await ch.send("conv-1", "hello")
        mock_target.send.assert_awaited_once_with("hello")

    async def test_send_long_message_chunked(self):
        ch = DiscordChannel(token="fake", config={})
        mock_target = AsyncMock()
        ch._conversations["conv-1"] = mock_target

        long_text = "a" * 3000
        await ch.send("conv-1", long_text)
        assert mock_target.send.await_count == 2

    async def test_send_typing(self):
        ch = DiscordChannel(token="fake", config={})
        mock_target = AsyncMock()
        ch._conversations["conv-1"] = mock_target

        await ch.send_typing("conv-1")
        mock_target.typing.assert_awaited_once()

    async def test_send_typing_unknown_conv(self):
        ch = DiscordChannel(token="fake", config={})
        await ch.send_typing("unknown")  # should not raise


# --- Main entry point channel setup tests ---


class TestSetupChannels:
    def test_no_discord_config(self):
        from inotagent.config.agent import AgentConfig
        from inotagent.main import setup_channels

        config = AgentConfig(name="test", model_id="m", channels={})
        loop = MagicMock()
        manager, discord_ch = setup_channels(config, loop)
        assert manager.has_channels() is False

    def test_discord_disabled(self):
        from inotagent.config.agent import AgentConfig
        from inotagent.main import setup_channels

        config = AgentConfig(name="test", model_id="m", channels={
            "discord": {"enabled": False, "token_env": "DISCORD_BOT_TOKEN"},
        })
        loop = MagicMock()
        manager, discord_ch = setup_channels(config, loop)
        assert manager.has_channels() is False

    def test_discord_enabled_no_token(self, monkeypatch):
        from inotagent.config.agent import AgentConfig
        from inotagent.main import setup_channels

        monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
        config = AgentConfig(name="test", model_id="m", channels={
            "discord": {"enabled": True, "token_env": "DISCORD_BOT_TOKEN"},
        })
        loop = MagicMock()
        manager, discord_ch = setup_channels(config, loop)
        assert manager.has_channels() is False

    def test_discord_enabled_with_token(self, monkeypatch):
        from inotagent.config.agent import AgentConfig
        from inotagent.main import setup_channels

        monkeypatch.setenv("DISCORD_BOT_TOKEN", "fake-token")
        config = AgentConfig(name="test", model_id="m", channels={
            "discord": {
                "enabled": True,
                "token_env": "DISCORD_BOT_TOKEN",
                "allowFrom": ["123"],
                "guilds": {"456": {"requireMention": True}},
            },
        })
        loop = MagicMock()
        manager, discord_ch = setup_channels(config, loop)
        assert manager.has_channels() is True

    def test_slack_enabled_with_tokens(self, monkeypatch):
        from inotagent.config.agent import AgentConfig
        from inotagent.main import setup_channels

        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-fake")
        monkeypatch.setenv("SLACK_APP_TOKEN", "xapp-fake")
        config = AgentConfig(name="test", model_id="m", channels={
            "slack": {"enabled": True},
        })
        loop = MagicMock()
        manager, discord_ch = setup_channels(config, loop)
        assert manager.has_channels() is True
        assert discord_ch is None  # no discord configured

    def test_slack_enabled_missing_app_token(self, monkeypatch):
        from inotagent.config.agent import AgentConfig
        from inotagent.main import setup_channels

        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-fake")
        monkeypatch.delenv("SLACK_APP_TOKEN", raising=False)
        config = AgentConfig(name="test", model_id="m", channels={
            "slack": {"enabled": True},
        })
        loop = MagicMock()
        manager, discord_ch = setup_channels(config, loop)
        assert manager.has_channels() is False

    def test_slack_disabled(self):
        from inotagent.config.agent import AgentConfig
        from inotagent.main import setup_channels

        config = AgentConfig(name="test", model_id="m", channels={
            "slack": {"enabled": False},
        })
        loop = MagicMock()
        manager, discord_ch = setup_channels(config, loop)
        assert manager.has_channels() is False

    def test_both_channels_enabled(self, monkeypatch):
        from inotagent.config.agent import AgentConfig
        from inotagent.main import setup_channels

        monkeypatch.setenv("DISCORD_BOT_TOKEN", "fake-token")
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-fake")
        monkeypatch.setenv("SLACK_APP_TOKEN", "xapp-fake")
        config = AgentConfig(name="test", model_id="m", channels={
            "discord": {
                "enabled": True,
                "token_env": "DISCORD_BOT_TOKEN",
                "allowFrom": ["123"],
                "guilds": {"456": {"requireMention": True}},
            },
            "slack": {"enabled": True},
        })
        loop = MagicMock()
        manager, discord_ch = setup_channels(config, loop)
        assert manager.has_channels() is True
        assert discord_ch is not None


# --- Slack conversation ID tests ---


class TestSlackGetConversationId:
    def test_dm_channel(self):
        result = slack_get_conversation_id("D123456", "im", None)
        assert result == "slack-dm-D123456"

    def test_channel(self):
        result = slack_get_conversation_id("C123456", "channel", None)
        assert result == "slack-channel-C123456"

    def test_thread(self):
        result = slack_get_conversation_id("C123456", "channel", "1234567890.123456")
        assert result == "slack-thread-C123456-1234567890.123456"

    def test_dm_with_thread(self):
        result = slack_get_conversation_id("D123456", "im", "1234567890.123456")
        assert result == "slack-thread-D123456-1234567890.123456"


# --- Slack split_message tests ---


class TestSlackSplitMessage:
    def test_short_message(self):
        assert slack_split_message("hello") == ["hello"]

    def test_empty_message(self):
        assert slack_split_message("") == [""]

    def test_exact_limit(self):
        text = "a" * 4000
        assert slack_split_message(text) == [text]

    def test_over_limit(self):
        text = "a" * 5000
        chunks = slack_split_message(text)
        assert len(chunks) == 2
        assert "".join(chunks) == text


# --- Slack channel unit tests ---


class TestSlackChannel:
    def test_set_message_handler(self):
        ch = SlackChannel(bot_token="xoxb-fake", app_token="xapp-fake", config={})
        handler = AsyncMock()
        ch.set_message_handler(handler)
        assert ch._handler is handler

    async def test_send_no_target(self):
        ch = SlackChannel(bot_token="xoxb-fake", app_token="xapp-fake", config={})
        # Should not raise even with unknown conversation
        await ch.send("unknown-conv", "hello")

    async def test_send_to_known_target(self):
        ch = SlackChannel(bot_token="xoxb-fake", app_token="xapp-fake", config={})
        ch._app = MagicMock()
        ch._app.client = AsyncMock()
        ch._conversations["conv-1"] = ("C123", "1234.5678")

        await ch.send("conv-1", "hello")
        ch._app.client.chat_postMessage.assert_awaited_once_with(
            channel="C123", text="hello", thread_ts="1234.5678",
        )

    def test_is_allowed_user_no_restriction(self):
        ch = SlackChannel(bot_token="xoxb-fake", app_token="xapp-fake", config={"allowFrom": []})
        assert ch._is_allowed_user("U12345") is True

    def test_is_allowed_user_in_list(self):
        ch = SlackChannel(bot_token="xoxb-fake", app_token="xapp-fake", config={"allowFrom": ["U12345"]})
        assert ch._is_allowed_user("U12345") is True

    def test_is_allowed_user_not_in_list(self):
        ch = SlackChannel(bot_token="xoxb-fake", app_token="xapp-fake", config={"allowFrom": ["U12345"]})
        assert ch._is_allowed_user("U99999") is False


# --- Telegram conversation ID tests ---


class TestTelegramGetConversationId:
    def test_private_chat(self):
        result = telegram_get_conversation_id(123456, "private")
        assert result == "telegram-dm-123456"

    def test_group_chat(self):
        result = telegram_get_conversation_id(-100999, "group")
        assert result == "telegram-group--100999"

    def test_supergroup_chat(self):
        result = telegram_get_conversation_id(-100888, "supergroup")
        assert result == "telegram-group--100888"


# --- Telegram split_message tests ---


class TestTelegramSplitMessage:
    def test_short_message(self):
        assert telegram_split_message("hello") == ["hello"]

    def test_empty_message(self):
        assert telegram_split_message("") == [""]

    def test_exact_limit(self):
        text = "a" * 4096
        assert telegram_split_message(text) == [text]

    def test_over_limit(self):
        text = "a" * 5000
        chunks = telegram_split_message(text)
        assert len(chunks) == 2
        assert "".join(chunks) == text


# --- Telegram channel unit tests ---


class TestTelegramChannel:
    def test_set_message_handler(self):
        ch = TelegramChannel(token="fake-token", config={})
        handler = AsyncMock()
        ch.set_message_handler(handler)
        assert ch._handler is handler

    async def test_send_no_target(self):
        ch = TelegramChannel(token="fake-token", config={})
        await ch.send("unknown-conv", "hello")

    async def test_send_to_known_target(self):
        ch = TelegramChannel(token="fake-token", config={})
        ch._app = MagicMock()
        ch._app.bot = AsyncMock()
        ch._conversations["conv-1"] = 123456

        await ch.send("conv-1", "hello")
        ch._app.bot.send_message.assert_awaited_once_with(chat_id=123456, text="hello")

    def test_is_allowed_user_no_restriction(self):
        ch = TelegramChannel(token="fake-token", config={"allowFrom": []})
        assert ch._is_allowed_user("123456") is True

    def test_is_allowed_user_in_list(self):
        ch = TelegramChannel(token="fake-token", config={"allowFrom": ["123456"]})
        assert ch._is_allowed_user("123456") is True

    def test_is_allowed_user_not_in_list(self):
        ch = TelegramChannel(token="fake-token", config={"allowFrom": ["123456"]})
        assert ch._is_allowed_user("999999") is False


# --- Setup channels: Telegram tests ---


class TestSetupChannelsTelegram:
    def test_telegram_enabled_with_token(self, monkeypatch):
        from inotagent.config.agent import AgentConfig
        from inotagent.main import setup_channels

        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
        config = AgentConfig(name="test", model_id="m", channels={
            "telegram": {"enabled": True},
        })
        loop = MagicMock()
        manager, discord_ch = setup_channels(config, loop)
        assert manager.has_channels() is True
        assert discord_ch is None

    def test_telegram_enabled_no_token(self, monkeypatch):
        from inotagent.config.agent import AgentConfig
        from inotagent.main import setup_channels

        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        config = AgentConfig(name="test", model_id="m", channels={
            "telegram": {"enabled": True},
        })
        loop = MagicMock()
        manager, discord_ch = setup_channels(config, loop)
        assert manager.has_channels() is False

    def test_telegram_disabled(self):
        from inotagent.config.agent import AgentConfig
        from inotagent.main import setup_channels

        config = AgentConfig(name="test", model_id="m", channels={
            "telegram": {"enabled": False},
        })
        loop = MagicMock()
        manager, discord_ch = setup_channels(config, loop)
        assert manager.has_channels() is False

    def test_all_three_channels(self, monkeypatch):
        from inotagent.config.agent import AgentConfig
        from inotagent.main import setup_channels

        monkeypatch.setenv("DISCORD_BOT_TOKEN", "fake")
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-fake")
        monkeypatch.setenv("SLACK_APP_TOKEN", "xapp-fake")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-tg")
        config = AgentConfig(name="test", model_id="m", channels={
            "discord": {
                "enabled": True,
                "token_env": "DISCORD_BOT_TOKEN",
                "allowFrom": ["123"],
                "guilds": {"456": {"requireMention": True}},
            },
            "slack": {"enabled": True},
            "telegram": {"enabled": True},
        })
        loop = MagicMock()
        manager, discord_ch = setup_channels(config, loop)
        assert manager.has_channels() is True
        assert discord_ch is not None
