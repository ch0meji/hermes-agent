import type { NashichanState } from "./types";

export const NASHICHAN_ASSETS: Readonly<Record<NashichanState, string>> = {
  idle: "/assets/nashichan/idle.png",
  greeting: "/assets/nashichan/greeting.png",
  listening: "/assets/nashichan/listening.png",
  thinking: "/assets/nashichan/thinking.png",
  working: "/assets/nashichan/working.png",
  approval: "/assets/nashichan/approval.png",
  success: "/assets/nashichan/success.png",
  celebrate: "/assets/nashichan/celebrate.png",
  warning: "/assets/nashichan/warning.png",
  error: "/assets/nashichan/error.png",
  offline: "/assets/nashichan/offline.png",
  security: "/assets/nashichan/security.png",
  update: "/assets/nashichan/update.png",
  sleep: "/assets/nashichan/sleep.png",
};

export const NASHICHAN_PRELOAD_STATES: readonly NashichanState[] = [
  "idle",
  "thinking",
  "working",
  "approval",
  "success",
  "warning",
  "error",
  "offline",
];
