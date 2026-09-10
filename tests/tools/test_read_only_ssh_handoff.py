"""Focused regression tests for read-only SSH Ops handoffs."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from plugins.platforms.discord.handoff import (
    OpsHandoff,
    build_ops_execution_prompt,
    extract_ops_result_metadata,
    format_ops_result,
    is_read_only_ssh_request,
)
from tools.read_only_ssh import is_read_only_ssh_command


@pytest.mark.parametrize(
    "command",
    [
        "ssh hermes-prod uptime",
        "ssh -o StrictHostKeyChecking=yes hermes-prod uptime -p",
        "ssh hermes-prod -- uname -r",
        "ssh alice@example.com hostname -s",
    ],
)
def test_known_host_read_only_ssh_command_is_safe(command):
    assert is_read_only_ssh_command(command) is True


@pytest.mark.parametrize(
    "command",
    [
        "ssh hermes-prod",
        "ssh hermes-prod rm -rf /",
        "ssh hermes-prod uptime; rm -rf /",
        "ssh hermes-prod uptime | tee /tmp/out",
        "ssh -o UserKnownHostsFile=/dev/null hermes-prod uptime",
        "ssh -o StrictHostKeyChecking=no hermes-prod uptime",
    ],
)
def test_non_read_only_or_unverified_ssh_command_is_not_safe(command):
    assert is_read_only_ssh_command(command) is False


def test_direct_read_only_ssh_bypasses_approval_prompt(monkeypatch):
    import tools.approval as approval

    monkeypatch.setattr(approval.approval_context, "_get_approval_mode", lambda: "ask")
    monkeypatch.setattr(approval, "_presence", lambda *_args: pytest.fail("approval prompt path reached"))
    monkeypatch.setattr(approval, "_tirith_scan", lambda *_args: pytest.fail("tirith scan path reached"))
    result = approval.check_all_command_guards("ssh hermes-prod uptime", "local")
    assert result["approved"] is True


def test_approval_timeout_is_blocked_with_machine_reason(monkeypatch):
    import tools.terminal_tool as terminal_tool

    monkeypatch.setattr(
        terminal_tool,
        "_check_all_guards",
        lambda *_args, **_kwargs: {
            "approved": False,
            "outcome": "timeout",
            "message": "approval request timed out",
        },
    )
    with pytest.raises(terminal_tool._Rejected) as raised:
        terminal_tool._run_approval_guards("rm -rf ./build", "local", {}, force=False)
    body = json.loads(raised.value.result_json)
    assert body["status"] == "blocked"
    assert body["reason"] == "approval_timeout"


def test_explicit_deny_stays_blocked_without_timeout_reason(monkeypatch):
    import tools.terminal_tool as terminal_tool

    monkeypatch.setattr(
        terminal_tool,
        "_check_all_guards",
        lambda *_args, **_kwargs: {
            "approved": False,
            "outcome": "blocked",
            "message": "command denied",
        },
    )
    with pytest.raises(terminal_tool._Rejected) as raised:
        terminal_tool._run_approval_guards("rm -rf ./build", "local", {}, force=False)
    body = json.loads(raised.value.result_json)
    assert body["status"] == "blocked"
    assert "reason" not in body


def test_read_only_ssh_backend_skips_connection_probe_and_sync(monkeypatch, tmp_path):
    from tools.environments import ssh as ssh_env

    monkeypatch.setattr(ssh_env.shutil, "which", lambda _name: "/usr/bin/ssh")
    establish = MagicMock(side_effect=AssertionError("read-only path must not preflight SSH"))
    monkeypatch.setattr(ssh_env.SSHEnvironment, "_establish_connection", establish)
    monkeypatch.setattr(ssh_env.tempfile, "gettempdir", lambda: str(tmp_path))
    env = ssh_env.SSHEnvironment(host="hermes-prod", user="alice", read_only=True)

    command = env._build_ssh_command()
    rendered = " ".join(command)
    assert "StrictHostKeyChecking=yes" in rendered
    assert "ControlMaster" not in rendered
    assert command[-1] == "alice@hermes-prod"
    assert env._sync_manager is None
    establish.assert_not_called()


def test_terminal_config_exposes_read_only_ssh_mode(monkeypatch):
    monkeypatch.setenv("TERMINAL_SSH_READ_ONLY", "true")
    from tools.terminal_tool import _get_env_config

    assert _get_env_config()["ssh_read_only"] is True


def test_read_only_ssh_skips_prompt_backend_probe(monkeypatch):
    import agent.prompt_builder as prompt_builder

    fake_terminal = MagicMock()
    fake_terminal._get_env_config.return_value = {"ssh_read_only": True}
    assert prompt_builder._run_backend_probe("ssh", fake_terminal) == ""


def test_read_only_handoff_prompt_forbids_tcp_probe():
    handoff = OpsHandoff(handoff_id="H-20260910-SSH", request="- hermes-prod の uptime を確認して")
    assert is_read_only_ssh_request(handoff.request) is True
    prompt = build_ops_execution_prompt(handoff)
    assert "TCP/port preflight" in prompt
    assert "handoff_id: H-20260910-SSH" in prompt
    assert "status: success" in prompt


def test_ops_result_preserves_id_and_blocked_reason():
    result = format_ops_result(
        "H-20260910-SSH",
        '{"status":"blocked","reason":"approval_timeout"}',
        status="blocked",
        reason="approval_timeout",
    )
    assert "handoff_id: H-20260910-SSH" in result
    assert "- status: blocked" in result
    assert "- reason: approval_timeout" in result
    assert extract_ops_result_metadata('{"status":"blocked","reason":"approval_timeout"}') == (
        "blocked",
        "approval_timeout",
    )
