import type { NashichanState } from "./types";

/**
 * Presentation-only artwork for each Nashichan state.
 *
 * Keep each state as an independent asset so one malformed image cannot make
 * every mascot state unavailable.
 */
export const NASHICHAN_ASSETS: Record<NashichanState, string> = {
  idle: "/assets/nashichan/idle.webp",
  greeting: "/assets/nashichan/greeting.webp",
  listening: "/assets/nashichan/listening.webp",
  thinking: "/assets/nashichan/thinking.webp",
  working: "/assets/nashichan/working.webp",
  approval: "/assets/nashichan/approval.webp",
  success: "/assets/nashichan/success.webp",
  celebrate: "/assets/nashichan/celebrate.webp",
  warning: "/assets/nashichan/warning.webp",
  error: "/assets/nashichan/error.webp",
  offline: "/assets/nashichan/offline.webp",
  security: "/assets/nashichan/security.webp",
  update: "/assets/nashichan/update.webp",
  sleep: "/assets/nashichan/sleep.webp",
};
