import { useState } from "react";

import {
  NASHICHAN_SPRITE,
  NASHICHAN_SPRITE_CELLS,
} from "@/lib/nashichan/assets";
import type { NashichanState } from "@/lib/nashichan/types";
import { cn } from "@/lib/utils";

interface NashichanAvatarProps {
  state: NashichanState;
  className?: string;
}

export function NashichanAvatar({ state, className }: NashichanAvatarProps) {
  const [failed, setFailed] = useState(false);
  const { column, row } = NASHICHAN_SPRITE_CELLS[state];

  if (failed) return null;

  return (
    <div
      role="img"
      aria-label={`ナシちゃん: ${state}`}
      className={cn(
        "relative aspect-square w-[150px] shrink-0 overflow-hidden select-none sm:w-[190px] lg:w-[230px] xl:w-[260px]",
        className,
      )}
    >
      <img
        src={NASHICHAN_SPRITE}
        alt=""
        aria-hidden="true"
        draggable={false}
        onError={() => setFailed(true)}
        className="pointer-events-none absolute left-0 top-0 h-[400%] w-[400%] max-w-none select-none"
        style={{
          transform: `translate(${-column * 25}%, ${-row * 25}%)`,
        }}
      />
    </div>
  );
}
