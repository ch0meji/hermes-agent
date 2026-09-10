import os

from . import adapter as _adapter
from .mention_guard import targets_other_bot_only
from .thread_workrooms import is_nashi_child_thread, maybe_create_natural_thread


_original_discord_message_admission = _adapter.DiscordAdapter._discord_message_admission
_original_dispatch_discord_message = _adapter.DiscordAdapter._dispatch_discord_message
_original_in_bot_thread = _adapter.DiscordAdapter._in_bot_thread


def _discord_message_admission_with_hatsugarasu_guard(self, message, *, claim):
    """Keep human messages explicitly aimed at Hatsugarasu out of Nashi's normal ingress."""
    author = getattr(message, "author", None)
    client_user = getattr(getattr(self, "_client", None), "user", None)
    if not getattr(author, "bot", False) and targets_other_bot_only(
        message,
        other_bot_user_id=self._hatsugarasu_bot_user_id(),
        other_bot_role_id=os.getenv("HATSUGARASU_ROLE_ID", "1545458279021285500"),
        self_bot_user_id=str(getattr(client_user, "id", "") or ""),
    ):
        return False, False
    return _original_discord_message_admission(self, message, claim=claim)


def _in_bot_or_nashi_workroom_thread(self, message):
    """Nashi's designated parent owns its child threads even when a human created them."""
    return is_nashi_child_thread(message) or _original_in_bot_thread(self, message)


async def _dispatch_discord_message_with_natural_threads(self, message):
    """Create a workroom for natural `スレッド作って` requests before invoking the LLM."""
    handled = await maybe_create_natural_thread(self, message)
    if handled is True:
        return True
    return await _original_dispatch_discord_message(self, message)


if not getattr(_adapter.DiscordAdapter, "_hatsugarasu_mention_guard_installed", False):
    _adapter.DiscordAdapter._discord_message_admission = _discord_message_admission_with_hatsugarasu_guard
    _adapter.DiscordAdapter._hatsugarasu_mention_guard_installed = True

if not getattr(_adapter.DiscordAdapter, "_nashi_thread_workrooms_installed", False):
    _adapter.DiscordAdapter._in_bot_thread = _in_bot_or_nashi_workroom_thread
    _adapter.DiscordAdapter._dispatch_discord_message = _dispatch_discord_message_with_natural_threads
    _adapter.DiscordAdapter._nashi_thread_workrooms_installed = True

register = _adapter.register

__all__ = ["register"]
