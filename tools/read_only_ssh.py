"""Strict classifier for single-command, read-only SSH invocations.

This is intentionally a small policy helper, not an SSH client. It recognizes
only commands that have one remote, informational command and no shell control
operators. The SSH backend is responsible for enforcing known-host policy.
"""

from __future__ import annotations

import os
import shlex
from typing import Any


_SAFE_SSH_FLAGS = frozenset({"-4", "-6"})
_SAFE_SSH_VALUE_OPTIONS = frozenset({"-F", "-i", "-l", "-p"})
_SAFE_REMOTE_COMMANDS = {
    "date": frozenset(),
    "hostname": frozenset({"-s"}),
    "id": frozenset({"-g", "-n", "-u", "-un"}),
    "pwd": frozenset(),
    "uname": frozenset({"-a", "-m", "-n", "-o", "-r", "-s", "-v"}),
    "uptime": frozenset({"-p"}),
    "whoami": frozenset(),
}


def _safe_ssh_option(value: str) -> bool:
    """Return whether an ``ssh -o`` option preserves the read-only policy."""
    key, separator, option_value = value.partition("=")
    if not separator:
        return False
    key = key.strip().lower()
    option_value = option_value.strip()
    if key in {"batchmode", "stricthostkeychecking"}:
        return option_value.lower() == "yes"
    if key == "connecttimeout":
        return option_value.isdigit() and 0 < int(option_value) <= 120
    # In particular, reject UserKnownHostsFile=/dev/null: a known-host check
    # must not be disabled by an option embedded in the command.
    return False


def _safe_remote_argv(argv: list[str]) -> bool:
    if not argv:
        return False
    command = os.path.basename(argv[0])
    allowed_args = _SAFE_REMOTE_COMMANDS.get(command)
    if allowed_args is None:
        return False
    return all(argument in allowed_args for argument in argv[1:])


def is_read_only_ssh_command(command: Any) -> bool:
    """Recognize a safe direct SSH command with one informational operation.

    Shell operators, interactive SSH, arbitrary remote commands, and write
    operations are rejected. This function does not perform DNS/network or
    host-key checks; the SSH client must still use strict known-host policy.
    """
    if not isinstance(command, str) or not command.strip():
        return False
    # Reject shell syntax before shlex tokenization. Newlines are also
    # rejected so a second command cannot be hidden in a multi-line string.
    if any(char in command for char in "\r\n;&|<>()$`"):
        return False
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return False
    if not tokens or os.path.basename(tokens.pop(0)) != "ssh":
        return False

    destination = None
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            index += 1
            break
        if token in _SAFE_SSH_FLAGS:
            index += 1
            continue
        if token in _SAFE_SSH_VALUE_OPTIONS:
            if index + 1 >= len(tokens):
                return False
            value = tokens[index + 1]
            if token == "-p" and (not value.isdigit() or not 0 < int(value) <= 65535):
                return False
            if not value or any(char in value for char in "\r\n;&|<>()$`"):
                return False
            index += 2
            continue
        if token == "-o":
            if index + 1 >= len(tokens) or not _safe_ssh_option(tokens[index + 1]):
                return False
            index += 2
            continue
        if token.startswith("-o") and len(token) > 2:
            if not _safe_ssh_option(token[2:]):
                return False
            index += 1
            continue
        if token.startswith("-p") and len(token) > 2:
            port = token[2:]
            if not port.isdigit() or not 0 < int(port) <= 65535:
                return False
            index += 1
            continue
        if token.startswith("-"):
            return False
        destination = token
        index += 1
        break

    if not destination or destination.startswith("-"):
        return False
    remote = tokens[index:]
    if remote[:1] == ["--"]:
        remote = remote[1:]
    return _safe_remote_argv(remote)
