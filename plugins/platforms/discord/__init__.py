from . import adapter as _adapter
from .mention_guard import targets_other_bot_only


_original_discord_message_admission = _adapter.DiscordAdapter._discord_message_admission


def _discord_message_admission_with_hatsugarasu_guard(self, message, *, claim):
    """Keep human messages explicitly aimed at Hatsugarasu out of Nashi's normal ingress."""
    author = getattr(message, "author", None)
    client_user = getattr(getattr(self, "_client", None), "user", None)
    if not getattr(author, "bot", False) and targets_other_bot_only(
        message,
        other_bot_user_id=self._hatsugarasu_bot_user_id(),
        self_bot_user_id=str(getattr(client_user, "id", "") or ""),
    ):
        return False, False
    return _original_discord_message_admission(self, message, claim=claim)


if not getattr(_adapter.DiscordAdapter, "_hatsugarasu_mention_guard_installed", False):
    _adapter.DiscordAdapter._discord_message_admission = _discord_message_admission_with_hatsugarasu_guard
    _adapter.DiscordAdapter._hatsugarasu_mention_guard_installed = True

register = _adapter.register

__all__ = ["register"]
