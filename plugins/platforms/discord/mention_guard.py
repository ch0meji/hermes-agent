from __future__ import annotations

import re
from typing import Any

_MENTION_RE = re.compile(r"<@!?(\d+)>")


def raw_mentioned_user_ids(message: Any) -> set[str]:
    """Return literal user mention IDs from Discord message content."""
    content = getattr(message, "content", "") or ""
    return {match.group(1) for match in _MENTION_RE.finditer(content)}


def targets_other_bot_only(
    message: Any,
    *,
    other_bot_user_id: str,
    self_bot_user_id: str,
) -> bool:
    """True when the raw message targets the other bot but not this bot."""
    other_id = str(other_bot_user_id or "").strip()
    self_id = str(self_bot_user_id or "").strip()
    if not other_id:
        return False
    mentions = raw_mentioned_user_ids(message)
    return other_id in mentions and (not self_id or self_id not in mentions)
