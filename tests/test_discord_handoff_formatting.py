from plugins.platforms.discord.handoff import format_ops_result


def test_format_ops_result_strips_duplicate_metadata_and_bullet_layer():
    payload = format_ops_result(
        "H-20260910-001",
        "status: success\n- hostname: `hermes-prod`\n- uptime: `up 1 minute`",
        status="success",
    )

    assert payload.count("status: success") == 1
    assert "- hostname: `hermes-prod`" in payload
    assert "- uptime: `up 1 minute`" in payload
    assert "- - hostname" not in payload
    assert "- - uptime" not in payload


def test_format_ops_result_keeps_single_blocked_reason():
    payload = format_ops_result(
        "H-20260910-002",
        "status: blocked\nreason: approval_timeout\n- approval request timed out",
        status="blocked",
        reason="approval_timeout",
    )

    assert payload.count("status: blocked") == 1
    assert payload.count("reason: approval_timeout") == 1
    assert "- approval request timed out" in payload
