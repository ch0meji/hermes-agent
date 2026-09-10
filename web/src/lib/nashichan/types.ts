import type { ConnectionState } from "@/lib/gatewayClient";

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

export interface HermesDashboardEvent {
  type?: string;
  payload?: unknown;
}

export interface NashichanConnectionInput {
  state: ConnectionState;
  hasError?: boolean;
}
