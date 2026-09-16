import { createPortal } from "react-dom";

import { NashichanAvatar } from "./NashichanAvatar";
import { NashichanBubble } from "./NashichanBubble";
import type { NashichanState } from "@/lib/nashichan/types";

interface NashichanPanelProps {
  state: NashichanState;
}

/**
 * Floating, non-interactive dashboard mascot. It is intentionally portaled
 * outside ChatSidebar so the mobile slide-over transform cannot trap the
 * fixed-position character layer.
 */
export function NashichanPanel({ state }: NashichanPanelProps) {
  if (typeof document === "undefined") return null;

  return createPortal(
    <div
      data-testid="nashichan-panel"
      data-state={state}
      className="pointer-events-none fixed bottom-12 right-2 z-30 flex items-end gap-2 sm:bottom-14 sm:right-3 lg:right-[16rem]"
    >
      <NashichanBubble
        state={state}
        className="mb-16 hidden max-w-[180px] sm:block lg:max-w-[220px]"
      />
      <NashichanAvatar state={state} />
    </div>,
    document.body,
  );
}
