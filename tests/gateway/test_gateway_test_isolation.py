"""P0 regressions for test/production Gateway isolation.

These tests intentionally use temporary "production-shaped" fixtures.  They
must never stop, replace, inspect, or signal the real Gateway runtime.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from gateway.test_isolation import (
    GatewayIsolationError,
    ProcessOwnership,
    assert_gateway_runtime_safe,
    assert_runtime_path_safe,
    assert_service_operation,
    capture_process_ownership,
    cleanup_owned_process_group,
    process_ownership_matches,
    require_isolated_test_environment,
    resolve_service_root,
)
from hermes_cli.service_manager import S6ServiceManager


def _set_isolated_env(monkeypatch: pytest.MonkeyPatch, root: Path) -> tuple[Path, Path, Path]:
    home = root / "hermes-home"
    state = home / "gateway-runtime"
    services = home / "s6-service"
    state.mkdir(parents=True)
    services.mkdir(parents=True)
    monkeypatch.setenv("HERMES_TEST_ISOLATION", str(home))
    monkeypatch.setenv("HERMES_TEST_PROFILE", "pytest-p0")
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("HERMES_TEST_STATE_ROOT", str(state))
    monkeypatch.setenv("HERMES_TEST_SERVICE_ROOT", str(services))
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
    monkeypatch.delenv("HERMES_DISCORD_BOT_TOKEN", raising=False)
    return home, state, services


def _tree_snapshot(root: Path) -> dict[str, tuple[int, str]]:
    result: dict[str, tuple[int, str]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            result[str(path.relative_to(root))] = (
                path.stat().st_mtime_ns,
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
    return result


def test_test_service_root_never_falls_back_to_production(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _set_isolated_env(monkeypatch, tmp_path)

    with pytest.raises(GatewayIsolationError, match="production service root"):
        resolve_service_root(Path("/run/service"))
    with pytest.raises(GatewayIsolationError):
        S6ServiceManager(scandir=Path("/run/service"))
    with pytest.raises(GatewayIsolationError):
        assert_service_operation(Path("/run/service"), "gateway-default", "stop")


def test_gateway_replace_requires_explicit_test_profile_state_and_service(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERMES_TEST_ISOLATION", "1")
    monkeypatch.setenv("HERMES_HOME", "/tmp/hermes-test-home")
    for name in ("HERMES_TEST_PROFILE", "HERMES_TEST_STATE_ROOT", "HERMES_TEST_SERVICE_ROOT"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(GatewayIsolationError, match="profile"):
        assert_gateway_runtime_safe(replace=True)
    with pytest.raises(GatewayIsolationError, match="profile"):
        require_isolated_test_environment()
    with pytest.raises(GatewayIsolationError):
        S6ServiceManager()


def test_production_data_and_token_are_rejected_in_test_context(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _set_isolated_env(monkeypatch, tmp_path)

    with pytest.raises(GatewayIsolationError, match="production"):
        assert_runtime_path_safe(Path("/opt/data/state.db"), label="state.db")
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "test-fixture-must-not-be-used")
    with pytest.raises(GatewayIsolationError, match="credential"):
        require_isolated_test_environment()


def test_test_s6_script_uses_isolated_home_not_production_data_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home, _state, services = _set_isolated_env(monkeypatch, tmp_path)
    script = S6ServiceManager._render_run_script(
        "pytest-p0",
        {
            "HERMES_HOME": str(home),
            "HERMES_TEST_ISOLATION": str(home),
            "HERMES_TEST_SERVICE_ROOT": str(services),
        },
    )
    assert f"cd {home}" in script
    assert "/opt/data" not in script
    assert "gateway run --replace" in script


def test_cleanup_only_terminates_owned_test_process_group(tmp_path: Path) -> None:
    del tmp_path
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        start_new_session=True,
    )
    owner = capture_process_ownership(proc.pid)
    assert owner.pid == proc.pid
    assert owner.pgid == proc.pid
    assert cleanup_owned_process_group(owner)
    proc.wait(timeout=5)
    assert proc.poll() is not None


def test_mismatched_process_ownership_cannot_signal_child() -> None:
    fake = ProcessOwnership(pid=os.getpid(), pgid=os.getpgrp(), start_time="not-the-current-process")
    assert not process_ownership_matches(fake)


def test_isolated_cleanup_preserves_production_gateway_fixture_identity(tmp_path: Path) -> None:
    """A test-owned group can be cleaned without changing the production fixture PID."""
    production = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        start_new_session=True,
    )
    test_child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        start_new_session=True,
    )
    production_owner: ProcessOwnership | None = None
    try:
        production_owner = capture_process_ownership(production.pid)
        test_owner = capture_process_ownership(test_child.pid)
        assert cleanup_owned_process_group(test_owner)
        test_child.wait(timeout=5)
        assert production.poll() is None
        assert process_ownership_matches(production_owner)
    finally:
        if test_child.poll() is None:
            cleanup_owned_process_group(capture_process_ownership(test_child.pid))
            test_child.wait(timeout=5)
        if production.poll() is None and production_owner is not None:
            cleanup_owned_process_group(production_owner)
            production.wait(timeout=5)


def test_isolated_runtime_does_not_modify_production_shaped_state_or_service(tmp_path: Path) -> None:
    """The P0 path performs no writes below a production-shaped fixture."""
    production = tmp_path / "production"
    (production / "run-service" / "gateway-default").mkdir(parents=True)
    (production / "sessions").mkdir()
    (production / "logs").mkdir()
    (production / "state.db").write_bytes(b"production-state")
    (production / "gateway-state.json").write_text('{"pid":1234}\n', encoding="utf-8")
    (production / "run-service" / "gateway-default" / "run").write_text("#!/bin/sh\n", encoding="utf-8")
    before = _tree_snapshot(production)

    env = os.environ.copy()
    env["HERMES_TEST_ISOLATION"] = str(tmp_path / "test-home")
    env["HERMES_TEST_PROFILE"] = "pytest-child"
    env["HERMES_HOME"] = str(tmp_path / "test-home")
    env["HERMES_TEST_STATE_ROOT"] = str(tmp_path / "test-state")
    env["HERMES_TEST_SERVICE_ROOT"] = str(tmp_path / "test-services")
    env.pop("DISCORD_BOT_TOKEN", None)
    env.pop("HERMES_DISCORD_BOT_TOKEN", None)
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from gateway.test_isolation import assert_gateway_runtime_safe; "
                "assert_gateway_runtime_safe(replace=True)"
            ),
        ],
        env=env,
        cwd=Path(__file__).parents[2],
        check=True,
        capture_output=True,
        text=True,
    )
    assert child.returncode == 0
    assert _tree_snapshot(production) == before
