import { describe, expect, it } from "vitest";

import { NASHICHAN_ASSETS } from "./assets";
import { NASHICHAN_STATES } from "./types";

describe("NASHICHAN_ASSETS", () => {
  it("maps every state to its independent WebP asset", () => {
    expect(Object.keys(NASHICHAN_ASSETS).sort()).toEqual(
      [...NASHICHAN_STATES].sort(),
    );

    for (const state of NASHICHAN_STATES) {
      expect(NASHICHAN_ASSETS[state]).toBe(`/assets/nashichan/${state}.webp`);
    }
  });

  it("does not depend on a sprite sheet", () => {
    expect(
      Object.values(NASHICHAN_ASSETS).every((asset) => !asset.includes("sprite")),
    ).toBe(true);
  });
});
