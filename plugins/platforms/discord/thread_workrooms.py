from __future__ import annotations

import os
import re
from typing import Any, Optional


_DEFAULT_THREAD_NAME = "作業スレッド"
_THREAD_NAME_MAX = 90
_THREAD_REQUEST_RE = re.compile(
    r"^\s*(?:(?P<name>.+?)(?:用)?(?:の)?)?スレッド(?:を)?作って(?:ください)?[。.!！]*\s*$",
    re.IGNORECASE,
)


def parse_thread_creation_request(content: str, *, bot_user_id: str = "") -> Optional[str]:
    """Return a Discord-safe thread name for a natural Japanese creation request."""
    text = str(content or "")
    if bot_user_id:
        text = re.sub(rf"<@!?{re.escape(str(bot_user_id))}>", "", text)
    match = _THREAD_REQUEST_RE.match(text.strip())
    if not match:
        return None
    name = (match.group("name") or "").strip()
    name = re.sub(r"(?:用|の)\s*$", "", name).strip()
    if not name:
        return _DEFAULT_THREAD_NAME
    return name[:_THREAD_NAME_MAX]


def primary_nashi_channel_id() -> str:
    """Configured parent whose child threads are Nashi workrooms."""
    return str(
        os.getenv("DISCORD_NASHI_CHANNEL_ID")
        or os.getenv("DISCORD_DEV_CHANNEL_ID")
        or ""
    ).strip()


def parent_channel_id(channel: Any) -> str:
    raw = getattr(channel, "parent_id", None)
    if raw is None:
        parent = getattr(channel, "parent", None)
        raw = getattr(parent, "id", None)
    return str(raw or "")


def is_primary_nashi_location(message: Any) -> bool:
    primary = primary_nashi_channel_id()
    if not primary:
        return False
    channel = getattr(message, "channel", None)
    channel_id = str(getattr(channel, "id", "") or "")
    return channel_id == primary or parent_channel_id(channel) == primary


def is_nashi_child_thread(message: Any) -> bool:
    primary = primary_nashi_channel_id()
    if not primary:
        return False
    channel = getattr(message, "channel", None)
    return bool(parent_channel_id(channel) == primary)


async def maybe_create_natural_thread(adapter: Any, message: Any) -> Optional[bool]:
    """Intercept an authorized natural-language thread request.

    Returns None when the message is not ours to intercept, otherwise True after handling it.
    Admission is checked without claiming the message so ordinary messages can still flow through
    the normal dispatcher unchanged.
    """
    author = getattr(message, "author", None)
    client_user = getattr(getattr(adapter, "_client", None), "user", None)
    if getattr(author, "bot", False) or client_user is None:
        return None

    bot_user_id = str(getattr(client_user, "id", "") or "")
    name = parse_thread_creation_request(getattr(message, "content", ""), bot_user_id=bot_user_id)
    if name is None:
        return None

    admitted, _ = adapter._discord_message_admission(message, claim=False)
    if not admitted:
        return None

    explicit_self = bool(adapter._self_is_explicitly_mentioned(message))
    if not is_primary_nashi_location(message) and not explicit_self:
        return None

    channel = getattr(message, "channel", None)
    if parent_channel_id(channel):
        # Discord does not support nested text-channel threads. Handle cleanly and do not send
        # the request to the LLM as if it were a normal task.
        reply = getattr(message, "reply", None)
        if callable(reply):
            await reply("🍐 ここはすでにスレッドだよ。親チャンネルで作ってね。", mention_author=False)
        return True

    create_thread = getattr(message, "create_thread", None)
    if not callable(create_thread):
        reply = getattr(message, "reply", None)
        if callable(reply):
            await reply("🍐 この場所ではスレッドを作れなかったよ。", mention_author=False)
        return True

    try:
        thread = await create_thread(name=name, auto_archive_duration=1440)
        thread_id = str(getattr(thread, "id", "") or "")
        if thread_id:
            adapter._threads.add(thread_id)
        send = getattr(thread, "send", None)
        if callable(send):
            await send("🍐 スレッドを作ったよ。ここではメンションなしで続けられるよ。")
    except Exception as exc:
        reply = getattr(message, "reply", None)
        if callable(reply):
            await reply(f"🍐 スレッド作成に失敗したよ: {type(exc).__name__}", mention_author=False)
    return True
