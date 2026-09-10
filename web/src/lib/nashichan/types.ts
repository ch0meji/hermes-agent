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

export type NashichanActivity =
  | "idle"
  | "greeting"
  | "listening"
  | "thinking"
  | "working"
  | "success"
  | "celebrate"
  | "warning"
  | "error"
  | "security"
  | "update"
  | "sleep";

/**
 * Presentation-only snapshot. Hermes remains the source of truth; this type
 * intentionally carries no callbacks or mutation methods.
 */
export interface NashichanRuntimeStatus {
  /** Raw PTY connection state from ChatPage. Unknown values fail closed to offline. */
  ptyState?: string | null;
  /** Optional structured activity when/if the dashboard exposes one. */
  activity?: NashichanActivity | null;
  approvalRequired?: boolean;
  hasError?: boolean;
  securityCheck?: boolean;
  updating?: boolean;
  sleeping?: boolean;
}
