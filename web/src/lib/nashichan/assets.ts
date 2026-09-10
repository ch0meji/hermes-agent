import type { NashichanState } from "./types";

const ASSET_ROOT = "/assets/nashichan";

export const NASHICHAN_ASSETS: Record<NashichanState, string> = {
  idle: `${ASSET_ROOT}/idle.webp`,
  greeting: `${ASSET_ROOT}/greeting.webp`,
  listening: `${ASSET_ROOT}/listening.webp`,
  thinking: `${ASSET_ROOT}/thinking.webp`,
  working: `${ASSET_ROOT}/working.webp`,
  approval: `${ASSET_ROOT}/approval.webp`,
  success: `${ASSET_ROOT}/success.webp`,
  celebrate: `${ASSET_ROOT}/celebrate.webp`,
  warning: `${ASSET_ROOT}/warning.webp`,
  error: `${ASSET_ROOT}/error.webp`,
  offline: `${ASSET_ROOT}/offline.webp`,
  security: `${ASSET_ROOT}/security.webp`,
  update: `${ASSET_ROOT}/update.webp`,
  sleep: `${ASSET_ROOT}/sleep.webp`,
};
