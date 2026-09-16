import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { ConnectionState } from "@/lib/gatewayClient";
import {
  nashichanStateForConnection,
  nashichanStateForEvent,
} from "@/lib/nashichan/state-machine";
import type { NashichanState } from "@/lib/nashichan/types";

interface UseNashichanStateOptions {
  connectionState: ConnectionState;
  hasConnectionError?: boolean;
}

export interface NashichanStateController {
  state: NashichanState;
  handleHermesEvent: (type?: string, payload?: unknown) => void;
}

/**
 * Presentation-only state controller for the Hermes dashboard mascot.
 * Hermes remains the source of truth; this hook never mutates agent/session state.
 */
export function useNashichanState({
  connectionState,
  hasConnectionError = false,
}: UseNashichanStateOptions): NashichanStateController {
  const [activityState, setActivityState] = useState<NashichanState>("idle");
  const transientTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTransient = useCallback(() => {
    if (transientTimerRef.current) {
      clearTimeout(transientTimerRef.current);
      transientTimerRef.current = null;
    }
  }, []);

  useEffect(() => clearTransient, [clearTransient]);

  const handleHermesEvent = useCallback(
    (type?: string, payload?: unknown) => {
      const decision = nashichanStateForEvent(type, payload);
      if (!decision) return;

      clearTransient();
      setActivityState(decision.state);

      if (decision.transientMs) {
        transientTimerRef.current = setTimeout(() => {
          transientTimerRef.current = null;
          setActivityState("idle");
        }, decision.transientMs);
      }
    },
    [clearTransient],
  );

  const state = useMemo(() => {
    const connection = nashichanStateForConnection(
      connectionState,
      hasConnectionError,
    );
    return connection?.state ?? activityState;
  }, [activityState, connectionState, hasConnectionError]);

  return { state, handleHermesEvent };
}
