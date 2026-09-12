import type { NashichanConnectionState, NashichanState } from "./types";

export interface NashichanStateDecision {
  state: NashichanState;
  /** Optional presentation-only dwell time before returning to idle. */
  transientMs?: number;
}

const SUCCESS_DWELL_MS = 3_500;
const CELEBRATE_DWELL_MS = 4_500;
const GREETING_DWELL_MS = 3_000;

function objectPayload(payload: unknown): Record<string, unknown> | null {
  return payload !== null && typeof payload === "object"
    ? (payload as Record<string, unknown>)
    : null;
}

/**
 * Map the dashboard sidecar connection to a mascot state.
 * `null` means the connection itself should not replace the current activity state.
 */
export function nashichanStateForConnection(
  state: NashichanConnectionState,
  hasError = false,
): NashichanStateDecision | null {
  if (hasError || state === "closed" || state === "error") {
    return { state: "offline" };
  }
  if (state === "connecting") {
    return { state: "working" };
  }
  return null;
}

/** Map Hermes structured events to presentation-only Nashichan states. */
export function nashichanStateForEvent(
  type: string | undefined,
  payload?: unknown,
): NashichanStateDecision | null {
  if (!type) return null;

  const data = objectPayload(payload);

  if (type === "reaction") {
    return { state: "celebrate", transientMs: CELEBRATE_DWELL_MS };
  }

  if (type === "message.complete") {
    return { state: "success", transientMs: SUCCESS_DWELL_MS };
  }

  if (
    type === "message.start" ||
    type === "message.delta" ||
    type === "thinking.delta" ||
    type === "reasoning.delta"
  ) {
    return { state: "thinking" };
  }

  if (type === "tool.complete") {
    // After a tool returns, Hermes usually resumes model reasoning.
    return { state: "thinking" };
  }

  if (
    type === "tool.start" ||
    type === "tool.generating" ||
    type.startsWith("tool.progress") ||
    type === "terminal.read.request" ||
    type === "preview.read.request" ||
    type === "preview.act.request" ||
    type === "window.read.request"
  ) {
    return { state: "working" };
  }

  if (
    type === "clarify.request" ||
    type === "approval.request" ||
    type === "mcp.setup.request"
  ) {
    return { state: "approval" };
  }

  if (type === "sudo.request" || type === "secret.request") {
    return { state: "security" };
  }

  if (
    type === "update.start" ||
    type === "update.progress" ||
    type === "updater.start" ||
    type === "updater.progress"
  ) {
    return { state: "update" };
  }

  if (type === "dashboard.new_session_requested") {
    return { state: "greeting", transientMs: GREETING_DWELL_MS };
  }

  if (type === "notification.show") {
    const level = String(data?.level ?? "").toLowerCase();
    const kind = String(data?.kind ?? "").toLowerCase();

    if (kind.includes("security") || kind.includes("credential")) {
      return { state: "security" };
    }
    if (level === "error" || level === "critical") {
      return { state: "error" };
    }
    if (level === "warning" || level === "warn") {
      return { state: "warning" };
    }
  }

  if (type === "notification.clear") {
    return { state: "idle" };
  }

  return null;
}

export const NASHICHAN_TRANSIENT_DURATIONS = {
  greeting: GREETING_DWELL_MS,
  success: SUCCESS_DWELL_MS,
  celebrate: CELEBRATE_DWELL_MS,
} as const;
