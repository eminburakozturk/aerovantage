const STORAGE_KEY = "aerovantage-alert-acks";

export interface AlertAckRecord {
  acknowledgedAt: string;
}

let snapshot: Record<string, AlertAckRecord> = {};
let snapshotJson = "";

function syncFromStorage(): Record<string, AlertAckRecord> {
  if (typeof window === "undefined") return snapshot;

  const raw = window.localStorage.getItem(STORAGE_KEY) ?? "";
  if (raw === snapshotJson) return snapshot;

  snapshotJson = raw;
  if (!raw) {
    snapshot = {};
    return snapshot;
  }

  try {
    const parsed = JSON.parse(raw) as Record<string, AlertAckRecord>;
    snapshot = parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    snapshot = {};
  }

  return snapshot;
}

function persist(store: Record<string, AlertAckRecord>): void {
  if (typeof window === "undefined") return;
  const nextJson = JSON.stringify(store);
  window.localStorage.setItem(STORAGE_KEY, nextJson);
  snapshot = store;
  snapshotJson = nextJson;
}

export function getAlertAcks(): Record<string, AlertAckRecord> {
  return syncFromStorage();
}

export function isAlertAcknowledged(alertId: string): boolean {
  return Boolean(syncFromStorage()[alertId]);
}

export function acknowledgeAlert(alertId: string): void {
  const store = { ...syncFromStorage() };
  store[alertId] = { acknowledgedAt: new Date().toISOString() };
  persist(store);
  window.dispatchEvent(new CustomEvent("aerovantage-alert-acks-changed"));
}

export function clearAlertAck(alertId: string): void {
  const store = { ...syncFromStorage() };
  delete store[alertId];
  persist(store);
  window.dispatchEvent(new CustomEvent("aerovantage-alert-acks-changed"));
}
