export const NASHICHAN_STATES = [
  "idle",
  "greeting",
  "listening",
  "thinking",
  "working",
  "approval",
  "success",
  "celebrate",
  "warning",
  "error",
  "offline",
  "security",
  "update",
  "sleep",
] as const;

export type NashichanState = (typeof NASHICHAN_STATES)[number];

/**
 * Stable presentation-facing connection contract. This intentionally mirrors
 * the dashboard gateway lifecycle without coupling mascot code to a particular
 * shared-package build artifact.
 */
export type NashichanConnectionState =
  | "idle"
  | "connecting"
  | "open"
  | "closed"
  | "error";

export interface HermesDashboardEvent {
  type?: string;
  payload?: unknown;
}

export interface NashichanConnectionInput {
  state: NashichanConnectionState;
  hasError?: boolean;
}
