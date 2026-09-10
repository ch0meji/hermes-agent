import type { NashichanState } from "./types";

const ASSET_ROOT = "/assets/nashichan";

export const NASHICHAN_ASSETS: Record<NashichanState, string> = {
  idle: `${ASSET_ROOT}/idle.png`,
  greeting: `${ASSET_ROOT}/greeting.png`,
  listening: `${ASSET_ROOT}/listening.png`,
  thinking: `${ASSET_ROOT}/thinking.png`,
  working: `${ASSET_ROOT}/working.png`,
  approval: `${ASSET_ROOT}/approval.png`,
  success: `${ASSET_ROOT}/success.png`,
  celebrate: `${ASSET_ROOT}/celebrate.png`,
  warning: `${ASSET_ROOT}/warning.png`,
  error: `${ASSET_ROOT}/error.png`,
  offline: `${ASSET_ROOT}/offline.png`,
  security: `${ASSET_ROOT}/security.png`,
  update: `${ASSET_ROOT}/update.png`,
  sleep: `${ASSET_ROOT}/sleep.png`,
};
