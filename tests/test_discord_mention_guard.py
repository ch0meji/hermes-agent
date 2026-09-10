from types import SimpleNamespace

from plugins.platforms.discord.mention_guard import (
    raw_mentioned_role_ids,
    raw_mentioned_user_ids,
    targets_other_bot_only,
)


HATSUGARASU_ID = "1545456768430121022"
HATSUGARASU_ROLE_ID = "1545458279021285500"
NASHI_ID = "1545113469244674209"


def message(content: str):
    return SimpleNamespace(content=content)


def test_raw_mentioned_user_ids_accepts_normal_and_legacy_discord_mentions():
    msg = message(f"<@{HATSUGARASU_ID}> hello <@!{NASHI_ID}>")
    assert raw_mentioned_user_ids(msg) == {HATSUGARASU_ID, NASHI_ID}


def test_raw_mentioned_role_ids_accepts_discord_role_mentions():
    msg = message(f"<@&{HATSUGARASU_ROLE_ID}> 生きてる？")
    assert raw_mentioned_role_ids(msg) == {HATSUGARASU_ROLE_ID}


def test_hatsugarasu_user_mention_is_for_nashi_to_ignore():
    assert targets_other_bot_only(
        message(f"<@{HATSUGARASU_ID}> 生きてる？"),
        other_bot_user_id=HATSUGARASU_ID,
        other_bot_role_id=HATSUGARASU_ROLE_ID,
        self_bot_user_id=NASHI_ID,
    ) is True


def test_hatsugarasu_role_mention_is_for_nashi_to_ignore():
    assert targets_other_bot_only(
        message(f"<@&{HATSUGARASU_ROLE_ID}> 生きてる？"),
        other_bot_user_id=HATSUGARASU_ID,
        other_bot_role_id=HATSUGARASU_ROLE_ID,
        self_bot_user_id=NASHI_ID,
    ) is True


def test_plain_message_is_not_blocked():
    assert targets_other_bot_only(
        message("生きてる？"),
        other_bot_user_id=HATSUGARASU_ID,
        other_bot_role_id=HATSUGARASU_ROLE_ID,
        self_bot_user_id=NASHI_ID,
    ) is False


def test_message_explicitly_mentioning_both_bots_is_not_blocked():
    assert targets_other_bot_only(
        message(f"<@&{HATSUGARASU_ROLE_ID}> <@{NASHI_ID}> 2人とも確認して"),
        other_bot_user_id=HATSUGARASU_ID,
        other_bot_role_id=HATSUGARASU_ROLE_ID,
        self_bot_user_id=NASHI_ID,
    ) is False
