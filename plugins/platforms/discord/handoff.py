"""Small, human-readable protocol for the Codex ↔ Hermes Discord bridge.

This module deliberately contains no Discord or gateway imports.  Admission remains the
adapter's responsibility; these helpers only parse trusted transport candidates and format
bounded, redacted results.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

OPS_HANDOFF_HEADER = "🐦 → 🍆 Ops handoff"
OPS_RESULT_HEADER = "🍆 → 🐦 Ops result"
OPS_HANDOFF_START = "[OPS_HANDOFF]"
OPS_HANDOFF_END = "[/OPS_HANDOFF]"
MAX_HANDOFF_ID_LENGTH = 64
MAX_HANDOFF_BODY_BYTES = 1400
MAX_HANDOFF_MESSAGE_CHARS = 1900
MAX_RESULT_TEXT_LENGTH = 1500

_HANDOFF_ID_RE = re.compile(r"^H-[A-Za-z0-9][A-Za-z0-9-]*$")
_FIELD_RE = re.compile(r"^([a-z][a-z_]*)\s*:\s*(.*)$", re.IGNORECASE)
_ALLOWED_FIELDS = {"type", "handoff_id", "from", "to", "repo", "ref", "commit"}


@dataclass(frozen=True)
class OpsHandoff:
    """Parsed handoff data passed to the existing Hermes agent execution path."""

    handoff_id: str
    request: str
    repo: str = ""
    ref: str = ""
    commit: str = ""


def is_valid_handoff_id(value: object) -> bool:
    value = str(value or "")
    return bool(
        3 <= len(value) <= MAX_HANDOFF_ID_LENGTH
        and _HANDOFF_ID_RE.fullmatch(value)
    )


def _clean_line(value: object, max_length: int = 300) -> str:
    text = str(value or "")
    text = "".join(ch if ch >= " " else " " for ch in text)
    return " ".join(text.split())[:max_length].strip()


def _protocol_body(content: object) -> Optional[str]:
    text = str(content or "").strip()
    if len(text) > MAX_HANDOFF_MESSAGE_CHARS:
        return None
    if OPS_HANDOFF_START in text:
        start = text.find(OPS_HANDOFF_START) + len(OPS_HANDOFF_START)
        end = text.find(OPS_HANDOFF_END, start)
        if end < 0:
            return None
        text = text[start:end].strip()
    return text


def parse_ops_handoff(content: object) -> Optional[OpsHandoff]:
    """Parse one canonical human-readable ``ops_handoff`` message.

    The canonical Discord payload starts with :data:`OPS_HANDOFF_HEADER`.  The explicit wrapper
    emitted by the Hatsugarasu Codex instruction is accepted as well, but its inner payload must
    still contain the same required fields.
    """
    text = _protocol_body(content)
    if not text or len(text.encode("utf-8")) > MAX_HANDOFF_BODY_BYTES:
        return None
    lines = [line.strip() for line in text.splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    if not lines or lines.pop(0) != OPS_HANDOFF_HEADER:
        return None

    fields: dict[str, str] = {}
    request_lines: list[str] = []
    in_request = False
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        match = _FIELD_RE.match(line)
        if match:
            key = match.group(1).lower()
            value = _clean_line(match.group(2))
            if key == "request":
                in_request = True
                if value:
                    request_lines.append(value)
            elif key in _ALLOWED_FIELDS:
                if key in fields:
                    return None
                fields[key] = value
            else:
                return None
            continue
        if not in_request or not line.startswith("- "):
            return None
        value = _clean_line(line[2:])
        if value:
            request_lines.append(value)

    if (
        fields.get("type") != "ops_handoff"
        or not is_valid_handoff_id(fields.get("handoff_id"))
        or fields.get("from") != "codex"
        or fields.get("to") != "hermes"
        or not request_lines
    ):
        return None
    return OpsHandoff(
        handoff_id=fields["handoff_id"],
        request="\n".join(f"- {line}" for line in request_lines),
        repo=fields.get("repo", ""),
        ref=fields.get("ref", ""),
        commit=fields.get("commit", ""),
    )


def build_ops_execution_prompt(handoff: OpsHandoff) -> str:
    """Turn a parsed handoff into a bounded prompt for the existing Hermes agent."""
    metadata = []
    for key, value in (("repo", handoff.repo), ("ref", handoff.ref), ("commit", handoff.commit)):
        if value:
            metadata.append(f"{key}: {_clean_line(value, 200)}")
    context = "\n".join(metadata)
    if context:
        context = f"\n{context}"
    return (
        "[Trusted Discord Ops handoff]\n"
        f"handoff_id: {handoff.handoff_id}{context}\n\n"
        "Execute the following request with Hermes' existing Ops capabilities. Follow the normal "
        "safety rules for destructive or dangerous actions. Return only a concise factual result; "
        "do not include credentials, tokens, full command output, full logs, or internal reasoning.\n"
        "request:\n"
        f"{handoff.request}"
    )


def format_ops_result(handoff_id: str, result: object, *, success: bool = True) -> str:
    """Build a Discord-safe result while preserving the incoming correlation ID."""
    from agent.redact import redact_sensitive_text

    status = "success" if success else "failure"
    body = redact_sensitive_text(str(result or "").strip(), force=True, redact_url_credentials=True)
    body = body.replace("\x00", " ").strip()
    if len(body) > MAX_RESULT_TEXT_LENGTH:
        body = body[: MAX_RESULT_TEXT_LENGTH - 24].rstrip() + "\n…[truncated]"
    if not body:
        body = "No result was returned."
    formatted = (
        f"{OPS_RESULT_HEADER}\n\n"
        "type: ops_result\n"
        f"handoff_id: {handoff_id}\n"
        "from: hermes\n"
        "to: codex\n\n"
        "result:\n"
        f"- status: {status}\n"
        + "\n".join(f"- {line}" for line in body.splitlines())
    )
    return formatted[:MAX_HANDOFF_MESSAGE_CHARS]


class HandoffDedupe:
    """Process-local duplicate guard for Discord message IDs and handoff IDs."""

    def __init__(self, max_entries: int = 1024) -> None:
        self._max_entries = max_entries
        self._message_ids: dict[str, None] = {}
        self._handoff_ids: dict[str, None] = {}

    def claim(self, message_id: object, handoff_id: str) -> bool:
        message_key = str(message_id or "").strip()
        if not message_key or message_key in self._message_ids or handoff_id in self._handoff_ids:
            return False
        self._message_ids[message_key] = None
        self._handoff_ids[handoff_id] = None
        self._trim(self._message_ids)
        self._trim(self._handoff_ids)
        return True

    def _trim(self, store: dict[str, None]) -> None:
        while len(store) > self._max_entries:
            store.pop(next(iter(store)))
