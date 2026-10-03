"""Discord bus contract tests for the Codex ↔ Hermes Ops handoff."""

import asyncio
import os
import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from gateway.config import Platform, PlatformConfig
from gateway.platforms.event import MessageType
from gateway.run_inbound import GatewayInboundMixin
from gateway.run_busy import GatewayBusySessionMixin
from gateway.session import SessionSource, build_session_key
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
    monkeypatch.delenv("DISCORD_CHANNEL_ROUTING", raising=False)

    adapter = discord_platform.DiscordAdapter(PlatformConfig(enabled=True, token="test-token"))
    adapter._client = SimpleNamespace(user=SimpleNamespace(id=999))
    adapter._text_batch_delay_seconds = 0
    adapter.handle_message = AsyncMock()
    adapter._test_channel_factory = FakeTextChannel
    adapter._test_thread_factory = FakeThread
    return adapter


def _message(
    adapter, *, author_id, bot, channel_id=18765, content=None, message_id=1,
    thread=False, thread_id=None, handoff_id="H-20260909-001",
):
    parent = adapter._test_channel_factory(channel_id)
    channel = adapter._test_thread_factory(thread_id or channel_id + 1, parent) if thread else parent
    return SimpleNamespace(
        id=message_id,
        content=content if content is not None else _valid_content(handoff_id),
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


@pytest.mark.parametrize("thread", [False, True])
@pytest.mark.asyncio
async def test_human_handoff_channel_and_thread_posts_are_never_dispatched(discord_adapter, thread):
    import plugins.platforms.discord.adapter as discord_platform

    discord_adapter._test_message_type = discord_platform.discord.MessageType.default
    discord_adapter._ready_event.set()
    message = _message(
        discord_adapter, author_id=42, bot=False, thread=thread,
        thread_id=32001 if thread else None, message_id=320 if thread else 319,
    )

    assert await discord_adapter._dispatch_discord_message(message) is False
    discord_adapter.handle_message.assert_not_awaited()


@pytest.mark.parametrize(
    ("author_id", "content"),
    [
        (1545113469244674209, _valid_content("H-20261003-101")),
        (1545456768430121022, _valid_content("H-20261003-102").replace("type: ops_handoff", "type: invalid")),
    ],
)
def test_thread_rejects_other_bots_and_malformed_handoffs(discord_adapter, author_id, content):
    import plugins.platforms.discord.adapter as discord_platform

    discord_adapter._test_message_type = discord_platform.discord.MessageType.default
    message = _message(
        discord_adapter, author_id=author_id, bot=True, thread=True,
        thread_id=32002 + author_id % 10, content=content, message_id=321 + author_id % 10,
    )

    assert discord_adapter._discord_message_admission(message, claim=True) == (False, False)


@pytest.mark.parametrize("author_id", [1545456768430121022, 1545113469244674209, 123456])
def test_normal_channel_bots_are_always_rejected(discord_adapter, monkeypatch, author_id):
    import plugins.platforms.discord.adapter as discord_platform

    discord_adapter._test_message_type = discord_platform.discord.MessageType.default
    monkeypatch.setenv("DISCORD_ALLOW_BOTS", "all")
    message = _message(
        discord_adapter, author_id=author_id, bot=True, channel_id=999,
        content="hello", message_id=100 + author_id,
    )

    assert discord_adapter._discord_message_admission(message, claim=True) == (False, False)


@pytest.mark.parametrize("route", ["nashi_drop", "notification_drop"])
def test_runtime_channel_drop_routes_reject_before_llm(discord_adapter, monkeypatch, route):
    import plugins.platforms.discord.adapter as discord_platform

    discord_adapter._test_message_type = discord_platform.discord.MessageType.default
    monkeypatch.setenv("DISCORD_ALLOW_ALL_USERS", "true")
    discord_adapter.config.extra["channel_routing"] = {"routes": {route: ["999"]}}
    message = _message(
        discord_adapter, author_id=42, bot=False, channel_id=999,
        content="hello", message_id=200 + len(route),
    )

    assert discord_adapter._discord_channel_route(message) == route
    assert discord_adapter._discord_message_admission(message, claim=True) == (False, False)


def test_runtime_route_conflict_fails_closed(discord_adapter):
    import plugins.platforms.discord.adapter as discord_platform

    discord_adapter._test_message_type = discord_platform.discord.MessageType.default
    discord_adapter.config.extra["channel_routing"] = {
        "routes": {"nashi_accept": ["999"], "nashi_drop": ["999"]},
    }
    message = _message(discord_adapter, author_id=42, bot=False, channel_id=999, content="hello", message_id=202)

    assert discord_adapter._discord_channel_route(message) == "route_conflict"
    assert discord_adapter._discord_message_admission(message, claim=True) == (False, False)


def test_runtime_guild_allowlist_drops_before_user_auth(discord_adapter):
    import plugins.platforms.discord.adapter as discord_platform

    discord_adapter._test_message_type = discord_platform.discord.MessageType.default
    discord_adapter.config.extra["channel_routing"] = {"allowed_guilds": ["701"]}
    message = _message(discord_adapter, author_id=42, bot=False, channel_id=999, content="hello", message_id=203)

    assert discord_adapter._discord_channel_route(message) == "guild_drop"
    assert discord_adapter._discord_message_admission(message, claim=True) == (False, False)


@pytest.mark.asyncio
async def test_nashi_accept_relaxes_mention_and_thread_creation(discord_adapter, monkeypatch):
    import plugins.platforms.discord.adapter as discord_platform

    discord_adapter._test_message_type = discord_platform.discord.MessageType.default
    monkeypatch.setenv("DISCORD_REQUIRE_MENTION", "true")
    monkeypatch.setenv("DISCORD_AUTO_THREAD", "true")
    monkeypatch.setenv("DISCORD_ALLOW_ALL_USERS", "true")
    discord_adapter.config.extra["channel_routing"] = {"routes": {"nashi_accept": ["999"]}}
    discord_adapter._auto_create_thread = AsyncMock()
    message = _message(discord_adapter, author_id=42, bot=False, channel_id=999, content="hello", message_id=204)

    assert discord_adapter._discord_message_admission(message, claim=True) == (True, False)
    assert await discord_adapter._handle_message(message) is True
    discord_adapter.handle_message.assert_awaited_once()
    assert discord_adapter.handle_message.await_args.args[0].preserve_message_boundary is False
    discord_adapter._auto_create_thread.assert_not_awaited()


@pytest.mark.asyncio
async def test_native_self_mention_metadata_is_preserved(discord_adapter, monkeypatch):
    import plugins.platforms.discord.adapter as discord_platform

    discord_adapter._test_message_type = discord_platform.discord.MessageType.default
    monkeypatch.setenv("DISCORD_ALLOW_ALL_USERS", "true")
    monkeypatch.setenv("DISCORD_HISTORY_BACKFILL", "false")
    message = _message(
        discord_adapter, author_id=42, bot=False, channel_id=999,
        content="<@999> hello", message_id=205,
    )
    message.mentions = [discord_adapter._client.user]

    assert await discord_adapter._handle_message(message) is True
    event = discord_adapter.handle_message.await_args.args[0]
    assert event.text == "hello"
    assert event.metadata["discord_native_self_mention"] is True


def test_gateway_surfaces_trusted_native_mention_metadata():
    event = SimpleNamespace(metadata={"discord_native_self_mention": True})
    source = SimpleNamespace(platform=Platform.DISCORD)

    prepared = GatewayInboundMixin._prepend_inbound_trusted_discord_addressing(
        event, source, "hello"
    )

    assert prepared.startswith("[Trusted Discord routing metadata:")
    assert prepared.endswith("\n\nhello")


def test_gateway_does_not_invent_trusted_metadata():
    event = SimpleNamespace(metadata={})
    source = SimpleNamespace(platform=Platform.DISCORD)

    assert GatewayInboundMixin._prepend_inbound_trusted_discord_addressing(event, source, "hello") == "hello"


def test_yaml_channel_routing_stays_adapter_local(monkeypatch):
    import plugins.platforms.discord.adapter as discord_platform

    monkeypatch.delenv("DISCORD_CHANNEL_ROUTING", raising=False)
    routing = {"routes": {"nashi_accept": ["fixture-channel"]}}
    seeded = discord_platform._apply_yaml_config(
        {"platforms": {"discord": {"extra": {"channel_routing": routing}}}},
        {},
    )

    assert seeded["channel_routing"] == routing
    assert "DISCORD_CHANNEL_ROUTING" not in os.environ


@pytest.mark.asyncio
async def test_dispatch_dedupes_discord_message_and_handoff_id(discord_adapter):
    import plugins.platforms.discord.adapter as discord_platform

    discord_adapter._test_message_type = discord_platform.discord.MessageType.default
    discord_adapter._ready_event.set()
    first = _message(
        discord_adapter, author_id=1545456768430121022, bot=True, message_id=21,
        thread=True, thread_id=31001,
    )
    assert await discord_adapter._dispatch_discord_message(first) is True
    assert await discord_adapter._dispatch_discord_message(first) is False

    same_handoff_new_message = _message(
        discord_adapter, author_id=1545456768430121022, bot=True, message_id=22,
        thread=True, thread_id=31002,
    )
    assert await discord_adapter._dispatch_discord_message(same_handoff_new_message) is False
    discord_adapter.handle_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_handoff_dispatch_bypasses_text_batch_and_runs_one_two_or_five_threads(discord_adapter):
    """Complete handoffs enter their own thread session immediately, even inside the text window."""
    import plugins.platforms.discord.adapter as discord_platform

    discord_adapter._test_message_type = discord_platform.discord.MessageType.default
    discord_adapter._ready_event.set()
    discord_adapter._text_batch_delay_seconds = 0.1
    del discord_adapter.handle_message  # exercise BasePlatformAdapter's real session guard
    discord_adapter.config.typing_indicator = False

    for count in (1, 2, 5):
        started = []
        finished = []
        active_keys = set()
        max_active = 0
        all_started = asyncio.Event()
        all_finished = asyncio.Event()
        release = asyncio.Event()

        async def hold_session(event):
            nonlocal max_active
            key = discord_adapter._event_session_key(event)
            started.append((event, key))
            active_keys.add(key)
            max_active = max(max_active, len(active_keys))
            if len(started) == count:
                all_started.set()
            await release.wait()
            active_keys.remove(key)
            finished.append(key)
            if len(finished) == count:
                all_finished.set()

        discord_adapter._message_handler = hold_session
        messages = [
            _message(
                discord_adapter,
                author_id=1545456768430121022,
                bot=True,
                message_id=1000 + count * 10 + index,
                thread=True,
                thread_id=30000 + count * 10 + index,
                handoff_id=f"H-20261003-{count * 10 + index:03d}",
            )
            for index in range(count)
        ]
        tasks = [asyncio.create_task(discord_adapter._dispatch_discord_message(message)) for message in messages]
        try:
            await asyncio.wait_for(all_started.wait(), timeout=2)
            assert len(started) == count
            assert len({key for _, key in started}) == count
            assert {event.source.chat_id for event, _ in started} == {
                str(message.channel.id) for message in messages
            }
            assert set(discord_adapter._active_sessions) == {key for _, key in started}
            assert max_active == count
            assert not discord_adapter._pending_text_batches
        finally:
            release.set()
        assert await asyncio.gather(*tasks) == [True] * count
        await asyncio.wait_for(all_finished.wait(), timeout=2)
        await asyncio.gather(*tuple(discord_adapter._background_tasks), return_exceptions=True)


@pytest.mark.asyncio
async def test_distinct_busy_handoff_ids_stay_separate_fifo_events():
    """Even a reused thread cannot collapse two Ops IDs into a pending text event."""
    class FakeRunner(GatewayBusySessionMixin):
        _BUSY_QUEUE_MAX_PENDING = 8

        def __init__(self):
            self.adapter = SimpleNamespace(_pending_messages={})
            self._state = SimpleNamespace(conversation=SimpleNamespace(queued_events=[]))
            self._draining = False

        def _is_user_authorized(self, _source):
            return True

        def _effective_busy_input_mode(self, _source):
            return "queue"

        async def _route_plaintext_approval_while_busy(self, _event, _key):
            return False

        def _adapter_for_source(self, _source):
            return self.adapter

        def _queue_depth(self, key, *, adapter=None):
            del key
            return len(adapter._pending_messages) + len(self._state.conversation.queued_events)

        def _session_state(self, _key):
            return self._state

    runner = FakeRunner()

    def handoff_event(handoff_id):
        source = SessionSource(
            platform=Platform.DISCORD,
            chat_id="thread-1",
            chat_type="thread",
            user_id="1545456768430121022",
            is_bot=True,
            thread_id="thread-1",
            parent_chat_id="18765",
            trusted_discord_handoff=True,
        )
        return SimpleNamespace(
            source=source,
            metadata={"discord_handoff": {"handoff_id": handoff_id}},
            internal=False,
            message_type=MessageType.TEXT,
            text=f"payload for {handoff_id}",
            preserve_message_boundary=True,
        )

    first = handoff_event("H-20261003-001")
    second = handoff_event("H-20261003-002")
    assert await runner._handle_active_session_busy_message(first, "thread-session") is True
    assert await runner._handle_active_session_busy_message(second, "thread-session") is True

    assert runner.adapter._pending_messages["thread-session"] is first
    assert runner._state.conversation.queued_events == [second]
    assert [first.text, second.text] == ["payload for H-20261003-001", "payload for H-20261003-002"]


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
    assert build_session_key(event.source, thread_sessions_per_user=False) == (
        f"agent:main:discord:thread:{message.channel.id}:{message.channel.id}"
    )
    assert event.metadata["discord_handoff"]["handoff_id"] == "H-20260909-001"
    assert event.preserve_message_boundary is True
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
