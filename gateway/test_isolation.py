"""Fail-closed guards for test Gateway runtime isolation.

The production Gateway is supervised by s6 under ``/run/service`` and keeps its
state below the production Hermes home (normally ``/opt/data``).  Pytest must
never discover those defaults by accident.  This module is deliberately
stdlib-only so it can be imported by the CLI, service manager, and test runner
without importing the Gateway runtime.
"""
from __future__ import annotations

import errno
import os
import signal
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


TEST_ISOLATION_ENV = "HERMES_TEST_ISOLATION"
TEST_PROFILE_ENV = "HERMES_TEST_PROFILE"
TEST_STATE_ROOT_ENV = "HERMES_TEST_STATE_ROOT"
TEST_SERVICE_ROOT_ENV = "HERMES_TEST_SERVICE_ROOT"

PRODUCTION_SERVICE_ROOT = Path("/run/service")
PRODUCTION_DATA_ROOT = Path("/opt/data")
PROTECTED_TOKEN_ENV_NAMES = frozenset(
    {"DISCORD_BOT_TOKEN", "HERMES_DISCORD_BOT_TOKEN"}
)


class GatewayIsolationError(RuntimeError):
    """A test attempted to use a production Gateway runtime resource."""


def _canonical(path: os.PathLike[str] | str) -> Path:
    return Path(path).expanduser().absolute().resolve(strict=False)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def running_under_test() -> bool:
    """Return true for pytest and for children that inherited our marker."""
    if os.environ.get(TEST_ISOLATION_ENV):
        return True
    if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("PYTEST_VERSION"):
        return True
    return "pytest" in sys.modules


def is_production_service_path(path: os.PathLike[str] | str) -> bool:
    return _is_relative_to(_canonical(path), _canonical(PRODUCTION_SERVICE_ROOT))


def is_production_data_path(path: os.PathLike[str] | str) -> bool:
    """Recognize the production data root and all of its descendants.

    Callers should apply this only to runtime/state paths, never to source-code
    paths.  The explicit root is retained even on developer machines where the
    repository itself also happens to live below ``/opt/data``.
    """
    return _is_relative_to(_canonical(path), _canonical(PRODUCTION_DATA_ROOT))


def _require_absolute(name: str, value: str) -> Path:
    if not value:
        raise GatewayIsolationError(
            f"test Gateway isolation requires {name}; refusing production fallback"
        )
    path = _canonical(value)
    if not Path(value).expanduser().is_absolute():
        raise GatewayIsolationError(f"test Gateway isolation requires absolute {name}")
    return path


def assert_no_production_credentials() -> None:
    """Reject inherited production Discord credentials without printing values."""
    if not running_under_test():
        return
    leaked = sorted(name for name in PROTECTED_TOKEN_ENV_NAMES if os.environ.get(name))
    if leaked:
        raise GatewayIsolationError(
            "test Gateway cannot use production credential environment: "
            + ", ".join(leaked)
        )


def require_isolated_test_environment(*, require_service: bool = True) -> tuple[Path, Path | None]:
    """Validate explicit test profile/state/service roots; never infer production defaults."""
    if not running_under_test():
        return _canonical(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))), None

    profile = os.environ.get(TEST_PROFILE_ENV, "").strip()
    if not profile:
        raise GatewayIsolationError(
            f"test Gateway isolation requires {TEST_PROFILE_ENV}; refusing default profile"
        )
    home = _require_absolute("HERMES_HOME", os.environ.get("HERMES_HOME", ""))
    state_value = os.environ.get(TEST_STATE_ROOT_ENV, "")
    state = _require_absolute(TEST_STATE_ROOT_ENV, state_value)
    service: Path | None = None
    if require_service:
        service = _require_absolute(TEST_SERVICE_ROOT_ENV, os.environ.get(TEST_SERVICE_ROOT_ENV, ""))

    for label, path in (("HERMES_HOME", home), (TEST_STATE_ROOT_ENV, state)):
        if is_production_data_path(path):
            raise GatewayIsolationError(
                f"test Gateway {label} resolves inside production /opt/data: {path}"
            )
    if service is not None and is_production_service_path(service):
        raise GatewayIsolationError(
            f"test Gateway service root resolves to production /run/service: {service}"
        )
    if state == service:
        raise GatewayIsolationError("test Gateway state root and service root must be distinct")
    assert_no_production_credentials()
    return home, service


def resolve_service_root(candidate: os.PathLike[str] | str | None) -> Path:
    """Resolve an s6 service root, rejecting the production default in tests."""
    if running_under_test():
        require_isolated_test_environment(require_service=True)
        if candidate is None:
            raise GatewayIsolationError(
                "test S6ServiceManager requires an explicit isolated service root"
            )
    path = _canonical(candidate if candidate is not None else PRODUCTION_SERVICE_ROOT)
    if running_under_test() and is_production_service_path(path):
        raise GatewayIsolationError(
            f"test S6 operation targets production service root: {path}"
        )
    return path


def assert_service_operation(
    service_root: os.PathLike[str] | str,
    service_name: str,
    operation: str,
) -> None:
    """Guard every s6 operation, including read-only status/list operations."""
    root = resolve_service_root(service_root)
    if running_under_test() and is_production_service_path(root):
        raise GatewayIsolationError(
            f"test cannot {operation} service {service_name!r} in production /run/service"
        )
    if running_under_test() and service_name == "gateway-default" and is_production_service_path(root):
        raise GatewayIsolationError(
            "test cannot operate production gateway-default"
        )


def assert_runtime_path_safe(path: os.PathLike[str] | str, *, label: str = "runtime path") -> Path:
    """Guard state, logs, markers, and DB paths against production fallback."""
    resolved = _canonical(path)
    if running_under_test() and is_production_data_path(resolved):
        raise GatewayIsolationError(
            f"test cannot access production {label}: {resolved}"
        )
    return resolved


def assert_gateway_runtime_safe(*, replace: bool = False) -> None:
    """Fail before a test Gateway can inspect or replace production PID/state."""
    if not running_under_test():
        return
    home, service = require_isolated_test_environment(require_service=True)
    assert_runtime_path_safe(home, label="Hermes home")
    assert_runtime_path_safe(
        os.environ[TEST_STATE_ROOT_ENV], label="state directory"
    )
    if service is None or is_production_service_path(service):
        raise GatewayIsolationError("test Gateway has no isolated service root")
    if replace:
        # A replacement is only meaningful inside the explicitly selected test
        # profile.  Do not probe /run/service or production PID files from pytest;
        # rejecting the missing/unsafe target is the fail-fast behavior.
        if not os.environ.get(TEST_PROFILE_ENV, "").strip():
            raise GatewayIsolationError("gateway run --replace requires an explicit test profile")
    assert_no_production_credentials()


@dataclass(frozen=True)
class ProcessOwnership:
    """Identity captured for one child process created by the test runner."""

    pid: int
    pgid: int
    start_time: str


def _proc_start_time(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except OSError as exc:
        raise GatewayIsolationError(f"cannot inspect child process {pid}: {exc}") from exc
    # comm may contain spaces and ')' characters; the final ')' before the state
    # field is the stable delimiter used by procfs.
    close = raw.rfind(")")
    if close < 0:
        raise GatewayIsolationError(f"malformed /proc/{pid}/stat")
    fields = raw[close + 2 :].split()
    if len(fields) <= 19:
        raise GatewayIsolationError(f"incomplete /proc/{pid}/stat")
    return fields[19]


def capture_process_ownership(pid: int) -> ProcessOwnership:
    """Capture PID, process group, and start time before any cleanup."""
    if pid <= 1:
        raise GatewayIsolationError(f"refusing unsafe child PID {pid}")
    try:
        pgid = os.getpgid(pid)
    except OSError as exc:
        raise GatewayIsolationError(f"cannot inspect child process group {pid}: {exc}") from exc
    if pgid <= 1 or pgid == os.getpgrp():
        raise GatewayIsolationError(
            f"child PID {pid} does not own a safe process group (pgid={pgid})"
        )
    return ProcessOwnership(pid=pid, pgid=pgid, start_time=_proc_start_time(pid))


def process_ownership_matches(owner: ProcessOwnership) -> bool:
    """Ensure PID reuse and process-group changes cannot redirect cleanup."""
    try:
        return (
            os.getpgid(owner.pid) == owner.pgid
            and owner.pgid > 1
            and owner.pgid != os.getpgrp()
            and _proc_start_time(owner.pid) == owner.start_time
        )
    except (OSError, GatewayIsolationError):
        # Popen's session leader may have exited while grandchildren remain.
        # A process group cannot be recreated with the same ID while it still
        # exists, so the captured ``pgid == pid`` remains an ownership proof.
        if owner.pgid != owner.pid or owner.pgid <= 1 or owner.pgid == os.getpgrp():
            return False
        killpg = getattr(os, "killpg", None)
        if killpg is None:
            return False
        try:
            killpg(owner.pgid, 0)
        except OSError:
            return False
        return True


def terminate_owned_process_group(
    owner: ProcessOwnership,
    *,
    sig: int = signal.SIGTERM,
) -> bool:
    """Signal only the captured child process group; never use name-based killing."""
    if not process_ownership_matches(owner):
        return False
    killpg = getattr(os, "killpg", None)
    if killpg is None:
        return False
    try:
        killpg(owner.pgid, sig)
    except ProcessLookupError:
        return False
    except PermissionError as exc:
        raise GatewayIsolationError(
            f"permission denied terminating owned process group {owner.pgid}"
        ) from exc
    except OSError as exc:
        if exc.errno == errno.ESRCH:
            return False
        raise
    return True


def cleanup_owned_process_group(owner: ProcessOwnership, *, grace_seconds: float = 2.0) -> bool:
    """Terminate an owned process group without broad ``pkill``/name matching."""
    del grace_seconds  # The caller owns the wait loop; this helper never sleeps blindly.
    if not terminate_owned_process_group(owner, sig=signal.SIGTERM):
        return False
    # The runner is already in its bounded cleanup path. Escalate only against
    # the same verified group; never fall back to a process-name search.
    kill_signal = getattr(signal, "SIGKILL", signal.SIGTERM)
    terminate_owned_process_group(owner, sig=kill_signal)
    return True


__all__ = [
    "GatewayIsolationError",
    "ProcessOwnership",
    "TEST_ISOLATION_ENV",
    "TEST_PROFILE_ENV",
    "TEST_SERVICE_ROOT_ENV",
    "TEST_STATE_ROOT_ENV",
    "assert_gateway_runtime_safe",
    "assert_no_production_credentials",
    "assert_runtime_path_safe",
    "assert_service_operation",
    "capture_process_ownership",
    "cleanup_owned_process_group",
    "is_production_data_path",
    "is_production_service_path",
    "process_ownership_matches",
    "require_isolated_test_environment",
    "resolve_service_root",
    "running_under_test",
]
