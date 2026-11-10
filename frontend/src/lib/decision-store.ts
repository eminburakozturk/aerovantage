const STORAGE_KEY = "aerovantage-decisions";

export type DecisionStatus = "pending" | "approved" | "postponed" | "rejected";

export interface StoredDecision {
  annotationId: string;
  status: DecisionStatus;
  updatedAt: string;
  recommendedAction?: string;
  label?: string;
  context?: string;
}

let snapshot: Record<string, StoredDecision> = {};
let snapshotJson = "";

function syncFromStorage(): Record<string, StoredDecision> {
  if (typeof window === "undefined") return snapshot;

  const raw = window.localStorage.getItem(STORAGE_KEY) ?? "";
  if (raw === snapshotJson) return snapshot;

  snapshotJson = raw;
  if (!raw) {
    snapshot = {};
    return snapshot;
  }

  try {
    const parsed = JSON.parse(raw) as Record<string, StoredDecision>;
    snapshot = parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    snapshot = {};
  }

  return snapshot;
}

function persist(store: Record<string, StoredDecision>): void {
  if (typeof window === "undefined") return;
  const nextJson = JSON.stringify(store);
  window.localStorage.setItem(STORAGE_KEY, nextJson);
  snapshot = store;
  snapshotJson = nextJson;
}

export function getDecisions(): Record<string, StoredDecision> {
  return syncFromStorage();
}

export function getDecisionStatus(annotationId: string): DecisionStatus {
  return syncFromStorage()[annotationId]?.status ?? "pending";
}

export function setDecisionStatus(
  annotationId: string,
  status: DecisionStatus,
  meta?: Pick<StoredDecision, "recommendedAction" | "label" | "context">,
): void {
  const store = { ...syncFromStorage() };
  store[annotationId] = {
    annotationId,
    status,
    updatedAt: new Date().toISOString(),
    ...meta,
  };
  persist(store);
  window.dispatchEvent(new CustomEvent("aerovantage-decisions-changed"));
}

export function isPendingDecision(annotationId: string): boolean {
  const status = getDecisionStatus(annotationId);
  return status === "pending" || status === "postponed";
}
