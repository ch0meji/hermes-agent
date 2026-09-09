"""Discord bus contract tests for the Codex ↔ Hermes Ops handoff."""

import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from gateway.config import Platform, PlatformConfig
from gateway.session import SessionSource
from plugins.platforms.discord.handoff import (
    MAX_HANDOFF_MESSAGE_CHARS,
    HandoffDedupe,
    format_ops_result,
    parse_ops_handoff,
)


def _ensure_discord_importable():
    """Keep protocol/admission tests runnable in the lean test environment."""
    if "discord" in sys.modules and hasattr(sys.modules["discord"], "__file__"):
        return
    from unittest.mock import MagicMock

    discord_mod = MagicMock()
    discord_mod.Intents.default.return_value = MagicMock()
    discord_mod.DMChannel = type("DMChannel", (), {})
    discord_mod.Thread = type("Thread", (), {})
    discord_mod.ForumChannel = type("ForumChannel", (), {})
    discord_mod.Forbidden = type("Forbidden", (Exception,), {})
    discord_mod.MessageType = SimpleNamespace(default=0, reply=19)
    discord_mod.Object = lambda *, id: SimpleNamespace(id=id)
    discord_mod.Interaction = object
    discord_mod.app_commands = SimpleNamespace(
        describe=lambda **kwargs: (lambda fn: fn),
        choices=lambda **kwargs: (lambda fn: fn),
        Choice=lambda **kwargs: SimpleNamespace(**kwargs),
    )
    discord_mod.opus.is_loaded.return_value = True
    commands_mod = MagicMock()
    commands_mod.Bot = MagicMock
    ext_mod = MagicMock()
    ext_mod.commands = commands_mod
    sys.modules.setdefault("discord", discord_mod)
    sys.modules.setdefault("discord.ext", ext_mod)
    sys.modules.setdefault("discord.ext.commands", commands_mod)
    sys.modules.setdefault("discord.opus", discord_mod.opus)


_ensure_discord_importable()


def _valid_content(handoff_id: str = "H-20260909-001") -> str:
    return (
        "🐦 → 🍆 Ops handoff\n\n"
        "type: ops_handoff\n"
        f"handoff_id: {handoff_id}\n"
        "from: codex\n"
        "to: hermes\n"
        "repo: ch0meji/nanomon\n"
        "ref: main\n\n"
        "request:\n"
        "- hermes-prod のuptimeを確認"
    )


def test_protocol_requires_canonical_fields_and_preserves_request():
    handoff = parse_ops_handoff(_valid_content())

    assert handoff is not None
    assert handoff.handoff_id == "H-20260909-001"
    assert handoff.request == "- hermes-prod のuptimeを確認"
    assert handoff.repo == "ch0meji/nanomon"
    assert handoff.ref == "main"

    for replacement in (
        ("type: ops_handoff", "type: other"),
        ("from: codex", "from: hermes"),
        ("to: hermes", "to: codex"),
        ("handoff_id: H-20260909-001", "handoff_id: missing"),
        ("request:\n- hermes-prod のuptimeを確認", "request:"),
    ):
        assert parse_ops_handoff(_valid_content().replace(*replacement)) is None


def test_protocol_accepts_hatsugarasu_wrapper():
    wrapped = "[OPS_HANDOFF]\n" + _valid_content() + "\n[/OPS_HANDOFF]"
    assert parse_ops_handoff(wrapped).handoff_id == "H-20260909-001"


def test_handoff_dedupe_claims_message_and_handoff_once():
    dedupe = HandoffDedupe(max_entries=2)

    assert dedupe.claim("discord-message-1", "H-1") is True
    assert dedupe.claim("discord-message-1", "H-1") is False
    assert dedupe.claim("discord-message-2", "H-1") is False
    assert dedupe.claim("discord-message-2", "H-2") is True


def test_result_preserves_id_redacts_and_bounds_output():
    result = format_ops_result(
        "H-20260909-001",
        "ghp_12345678901234567890\n" + "large output " * 300,
    )

    assert len(result) <= MAX_HANDOFF_MESSAGE_CHARS
    assert "type: ops_result" in result
    assert "handoff_id: H-20260909-001" in result
    assert "ghp_12345678901234567890" not in result
    assert "status: success" in result


@pytest.fixture
def discord_adapter(monkeypatch):
    import plugins.platforms.discord.adapter as discord_platform

    class FakeDMChannel:
        pass

    class FakeThread:
        def __init__(self, channel_id, parent):
            self.id = channel_id
            self.name = "ops-thread"
            self.parent = parent
            self.parent_id = parent.id
            self.guild = parent.guild
            self.topic = None

    class FakeTextChannel:
        def __init__(self, channel_id):
            self.id = channel_id
            self.name = "ai-handoff"
            self.guild = SimpleNamespace(id=700, name="Hermes")
            self.topic = None

    monkeypatch.setattr(discord_platform.discord, "DMChannel", FakeDMChannel, raising=False)
    monkeypatch.setattr(discord_platform.discord, "Thread", FakeThread, raising=False)
    monkeypatch.setenv("DISCORD_HANDOFF_CHANNEL_ID", "18765")
    monkeypatch.setenv("HATSUGARASU_BOT_USER_ID", "1545456768430121022")
    monkeypatch.setenv("DISCORD_AUTO_THREAD", "false")
    monkeypatch.setenv("DISCORD_REQUIRE_MENTION", "true")
    monkeypatch.delenv("DISCORD_ALLOW_BOTS", raising=False)
    monkeypatch.delenv("DISCORD_ALLOWED_CHANNELS", raising=False)
    monkeypatch.delenv("DISCORD_IGNORED_CHANNELS", raising=False)

    adapter = discord_platform.DiscordAdapter(PlatformConfig(enabled=True, token="test-token"))
    adapter._client = SimpleNamespace(user=SimpleNamespace(id=999))
    adapter._text_batch_delay_seconds = 0
    adapter.handle_message = AsyncMock()
    adapter._test_channel_factory = FakeTextChannel
    adapter._test_thread_factory = FakeThread
    return adapter


def _message(adapter, *, author_id, bot, channel_id=18765, content=None, message_id=1, thread=False):
    parent = adapter._test_channel_factory(channel_id)
    channel = adapter._test_thread_factory(channel_id + 1, parent) if thread else parent
    return SimpleNamespace(
        id=message_id,
        content=content if content is not None else _valid_content(),
        mentions=[],
        attachments=[],
        reference=None,
        created_at=datetime.now(timezone.utc),
        channel=channel,
        guild=parent.guild,
        author=SimpleNamespace(
            id=author_id,
            bot=bot,
            name="Hatsugarasu" if bot else "Human",
            display_name="Hatsugarasu" if bot else "Human",
        ),
        type=adapter._test_message_type,
    )


def test_admission_is_channel_sender_and_protocol_specific(discord_adapter, monkeypatch):
    import plugins.platforms.discord.adapter as discord_platform

    discord_adapter._test_message_type = discord_platform.discord.MessageType.default
    valid_hatsu = _message(
        discord_adapter, author_id=1545456768430121022, bot=True, message_id=1,
    )
    assert discord_adapter._discord_message_admission(valid_hatsu, claim=True) == (True, False)

    for invalid in (
        _message(discord_adapter, author_id=1545113469244674209, bot=True, message_id=2),
        _message(discord_adapter, author_id=123456, bot=True, message_id=3),
        _message(discord_adapter, author_id=42, bot=False, message_id=4),
        _message(
            discord_adapter, author_id=1545456768430121022, bot=True,
            content=_valid_content().replace("type: ops_handoff", "type: invalid"), message_id=5,
        ),
    ):
        assert discord_adapter._discord_message_admission(invalid, claim=True) == (False, False)

    normal = _message(discord_adapter, author_id=1545456768430121022, bot=True, channel_id=999, message_id=6)
    assert discord_adapter._discord_message_admission(normal, claim=True) == (False, False)

    # A global bot opt-in must not turn an Ops payload in a normal channel into a normal
    # conversation or a handoff.
    monkeypatch.setenv("DISCORD_ALLOW_BOTS", "all")
    normal_with_global_bot_opt_in = _message(
        discord_adapter, author_id=1545456768430121022, bot=True, channel_id=999,
        message_id=8,
    )
    assert discord_adapter._discord_message_admission(normal_with_global_bot_opt_in, claim=True) == (False, False)


@pytest.mark.asyncio
async def test_dispatch_dedupes_discord_message_and_handoff_id(discord_adapter):
    import plugins.platforms.discord.adapter as discord_platform

    discord_adapter._test_message_type = discord_platform.discord.MessageType.default
    discord_adapter._ready_event.set()
    first = _message(
        discord_adapter, author_id=1545456768430121022, bot=True, message_id=21,
    )
    assert await discord_adapter._dispatch_discord_message(first) is True
    assert await discord_adapter._dispatch_discord_message(first) is False

    same_handoff_new_message = _message(
        discord_adapter, author_id=1545456768430121022, bot=True, message_id=22,
    )
    assert await discord_adapter._dispatch_discord_message(same_handoff_new_message) is False
    discord_adapter.handle_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_valid_handoff_reaches_existing_event_path_and_keeps_thread(discord_adapter):
    import plugins.platforms.discord.adapter as discord_platform

    discord_adapter._test_message_type = discord_platform.discord.MessageType.default
    message = _message(
        discord_adapter, author_id=1545456768430121022, bot=True, message_id=7, thread=True,
    )
    admitted, role_authorized = discord_adapter._discord_message_admission(message, claim=True)
    assert (admitted, role_authorized) == (True, False)

    assert await discord_adapter._handle_message(
        message, role_authorized=role_authorized,
        handoff=discord_adapter._parse_discord_handoff(message),
    ) is True
    event = discord_adapter.handle_message.await_args.args[0]
    assert event.source.trusted_discord_handoff is True
    assert event.source.is_bot is True
    assert "trusted_discord_handoff" not in event.source.to_dict()
    assert event.source.chat_type == "thread"
    assert event.source.thread_id == str(message.channel.id)
    assert event.source.parent_chat_id == "18765"
    assert event.metadata["discord_handoff"]["handoff_id"] == "H-20260909-001"
    assert "hermes-prod のuptimeを確認" in event.text


def test_central_authz_accepts_only_adapter_trusted_handoff(discord_adapter):
    from gateway.run import GatewayRunner

    source = SessionSource(
        platform=Platform.DISCORD,
        chat_id="18765",
        chat_type="channel",
        user_id="1545456768430121022",
        is_bot=True,
        trusted_discord_handoff=True,
    )
    runner = object.__new__(GatewayRunner)
    runner.adapters = {Platform.DISCORD: discord_adapter}
    runner._profile_adapters = {}
    runner.pairing_store = SimpleNamespace(is_approved=lambda *_args, **_kwargs: False)
    source._transport_adapter_ref = __import__("weakref").ref(discord_adapter)

    assert runner._is_user_authorized(source) is True

    source.user_id = "123456"
    assert runner._is_user_authorized(source) is False
