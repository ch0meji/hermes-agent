import asyncio
from types import SimpleNamespace

from plugins.platforms.discord.thread_workrooms import (
    is_nashi_child_thread,
    is_primary_nashi_location,
    maybe_create_natural_thread,
    parse_thread_creation_request,
)


NASHI_ID = "1545113469244674209"


def test_parse_thread_creation_request_default_and_named():
    assert parse_thread_creation_request("スレッド作って", bot_user_id=NASHI_ID) == "作業スレッド"
    assert parse_thread_creation_request("スレッドを作って", bot_user_id=NASHI_ID) == "作業スレッド"
    assert parse_thread_creation_request("NANOMON本番用のスレッド作って", bot_user_id=NASHI_ID) == "NANOMON本番"
    assert parse_thread_creation_request("melinda保守のスレッドを作って", bot_user_id=NASHI_ID) == "melinda保守"
    assert parse_thread_creation_request(f"<@{NASHI_ID}> nanomon開発用のスレッド作って", bot_user_id=NASHI_ID) == "nanomon開発"
    assert parse_thread_creation_request("普通の作業をして", bot_user_id=NASHI_ID) is None


def test_nashi_parent_and_child_detection(monkeypatch):
    monkeypatch.setenv("DISCORD_NASHI_CHANNEL_ID", "111111111111111")
    parent_message = SimpleNamespace(channel=SimpleNamespace(id=111111111111111, parent_id=None))
    child_message = SimpleNamespace(channel=SimpleNamespace(id=222222222222222, parent_id=111111111111111))
    other_message = SimpleNamespace(channel=SimpleNamespace(id=333333333333333, parent_id=444444444444444))
    assert is_primary_nashi_location(parent_message) is True
    assert is_primary_nashi_location(child_message) is True
    assert is_nashi_child_thread(child_message) is True
    assert is_nashi_child_thread(other_message) is False


def test_natural_thread_creation_uses_message_thread_and_registers(monkeypatch):
    monkeypatch.setenv("DISCORD_NASHI_CHANNEL_ID", "111111111111111")
    sent = []
    created = []

    class Thread:
        id = 222222222222222

        async def send(self, content):
            sent.append(content)

    async def create_thread(**kwargs):
        created.append(kwargs)
        return Thread()

    message = SimpleNamespace(
        content="NANOMON本番用のスレッド作って",
        author=SimpleNamespace(bot=False),
        channel=SimpleNamespace(id=111111111111111, parent_id=None),
        create_thread=create_thread,
    )
    adapter = SimpleNamespace(
        _client=SimpleNamespace(user=SimpleNamespace(id=int(NASHI_ID))),
        _threads=set(),
        _discord_message_admission=lambda _message, claim: (True, False),
        _self_is_explicitly_mentioned=lambda _message: False,
    )

    assert asyncio.run(maybe_create_natural_thread(adapter, message)) is True
    assert created == [{"name": "NANOMON本番", "auto_archive_duration": 1440}]
    assert adapter._threads == {"222222222222222"}
    assert sent and "メンションなし" in sent[0]


def test_unrelated_channel_without_explicit_mention_is_not_intercepted(monkeypatch):
    monkeypatch.setenv("DISCORD_NASHI_CHANNEL_ID", "111111111111111")
    message = SimpleNamespace(
        content="スレッド作って",
        author=SimpleNamespace(bot=False),
        channel=SimpleNamespace(id=333333333333333, parent_id=None),
    )
    adapter = SimpleNamespace(
        _client=SimpleNamespace(user=SimpleNamespace(id=int(NASHI_ID))),
        _discord_message_admission=lambda _message, claim: (True, False),
        _self_is_explicitly_mentioned=lambda _message: False,
    )
    assert asyncio.run(maybe_create_natural_thread(adapter, message)) is None
