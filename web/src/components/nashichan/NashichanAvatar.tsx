import { useState } from "react";

import { NASHICHAN_ASSETS } from "@/lib/nashichan/assets";
import type { NashichanState } from "@/lib/nashichan/types";
import { cn } from "@/lib/utils";

interface NashichanAvatarProps {
  state: NashichanState;
  className?: string;
}

export function NashichanAvatar({ state, className }: NashichanAvatarProps) {
  const src = NASHICHAN_ASSETS[state];
  const [failedSrc, setFailedSrc] = useState<string | null>(null);

  if (failedSrc === src) return null;

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
        src={src}
        alt=""
        aria-hidden="true"
        draggable={false}
        onError={() => setFailedSrc(src)}
        className="pointer-events-none h-full w-full select-none object-contain"
      />
    </div>
  );
}
