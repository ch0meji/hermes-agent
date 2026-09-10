from __future__ import annotations

import re
from typing import Any

_USER_MENTION_RE = re.compile(r"<@!?(\d+)>")
_ROLE_MENTION_RE = re.compile(r"<@&(\d+)>")


def raw_mentioned_user_ids(message: Any) -> set[str]:
    """Return literal user mention IDs from Discord message content."""
    content = getattr(message, "content", "") or ""
    return {match.group(1) for match in _USER_MENTION_RE.finditer(content)}


def raw_mentioned_role_ids(message: Any) -> set[str]:
    """Return literal role mention IDs from Discord message content."""
    content = getattr(message, "content", "") or ""
    return {match.group(1) for match in _ROLE_MENTION_RE.finditer(content)}


def targets_other_bot_only(
    message: Any,
    *,
    other_bot_user_id: str,
    self_bot_user_id: str,
    other_bot_role_id: str = "",
) -> bool:
    """True when the raw message targets the other bot (user or role) but not this bot."""
    other_user_id = str(other_bot_user_id or "").strip()
    other_role_id = str(other_bot_role_id or "").strip()
    self_id = str(self_bot_user_id or "").strip()

    user_mentions = raw_mentioned_user_ids(message)
    role_mentions = raw_mentioned_role_ids(message)
    other_targeted = (
        (bool(other_user_id) and other_user_id in user_mentions)
        or (bool(other_role_id) and other_role_id in role_mentions)
    )
    self_targeted = bool(self_id) and self_id in user_mentions
    return other_targeted and not self_targeted
