"use client";

import { useCallback, useSyncExternalStore } from "react";

import {
  type DecisionStatus,
  type StoredDecision,
  getDecisions,
  setDecisionStatus,
} from "@/lib/decision-store";

function subscribe(callback: () => void): () => void {
  const handler = () => callback();
  window.addEventListener("storage", handler);
  window.addEventListener("aerovantage-decisions-changed", handler);
  return () => {
    window.removeEventListener("storage", handler);
    window.removeEventListener("aerovantage-decisions-changed", handler);
  };
}

const EMPTY_DECISIONS: Record<string, StoredDecision> = {};

export function useDecisionStore() {
  const decisions = useSyncExternalStore(subscribe, getDecisions, () => EMPTY_DECISIONS);

  const setStatus = useCallback(
    (
      annotationId: string,
      status: DecisionStatus,
      meta?: { recommendedAction?: string; label?: string; context?: string },
    ) => {
      setDecisionStatus(annotationId, status, meta);
    },
    [],
  );

  const getStatus = useCallback(
    (annotationId: string) => decisions[annotationId]?.status ?? "pending",
    [decisions],
  );

  const isPending = useCallback((annotationId: string) => {
    const status = decisions[annotationId]?.status ?? "pending";
    return status === "pending" || status === "postponed";
  }, [decisions]);

  return { decisions, setStatus, getStatus, isPending };
}
