import type { NashichanState } from "@/lib/nashichan/types";
import { NASHICHAN_MESSAGES } from "@/lib/nashichan/messages";
import { cn } from "@/lib/utils";

interface NashichanBubbleProps {
  state: NashichanState;
  className?: string;
}

export function NashichanBubble({ state, className }: NashichanBubbleProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "max-w-[220px] rounded-2xl border border-current/15 bg-background-base/90 px-3 py-2 text-xs text-midground shadow-lg backdrop-blur-sm",
        className,
      )}
    >
      {NASHICHAN_MESSAGES[state]}
    </div>
  );
}
