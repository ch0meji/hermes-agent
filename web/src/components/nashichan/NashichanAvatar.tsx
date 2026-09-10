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
  const [failedAsset, setFailedAsset] = useState<string | null>(null);

  if (failedAsset === src) return null;

  return (
    <img
      src={src}
      alt={`ナシちゃん: ${state}`}
      draggable={false}
      onError={() => setFailedAsset(src)}
      className={cn(
        "block h-auto w-[150px] select-none object-contain sm:w-[190px] lg:w-[230px] xl:w-[260px]",
        className,
      )}
    />
  );
}
