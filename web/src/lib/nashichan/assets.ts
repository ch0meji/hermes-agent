import type { NashichanState } from "./types";

export const NASHICHAN_SPRITE = "/assets/nashichan/nashichan-sprite.webp";

export interface NashichanSpriteCell {
  column: number;
  row: number;
}

/**
 * 4x4 sprite coordinates. Keeping every approved state in one binary asset
 * avoids fourteen independent image requests and keeps state artwork atomic.
 */
export const NASHICHAN_SPRITE_CELLS: Record<NashichanState, NashichanSpriteCell> = {
  idle: { column: 0, row: 0 },
  greeting: { column: 1, row: 0 },
  listening: { column: 2, row: 0 },
  thinking: { column: 3, row: 0 },
  working: { column: 0, row: 1 },
  approval: { column: 1, row: 1 },
  success: { column: 2, row: 1 },
  celebrate: { column: 3, row: 1 },
  warning: { column: 0, row: 2 },
  error: { column: 1, row: 2 },
  offline: { column: 2, row: 2 },
  security: { column: 3, row: 2 },
  update: { column: 0, row: 3 },
  sleep: { column: 1, row: 3 },
};
