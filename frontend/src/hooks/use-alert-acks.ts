"use client";

import { useCallback, useSyncExternalStore } from "react";

import { acknowledgeAlert, clearAlertAck, getAlertAcks, type AlertAckRecord } from "@/lib/alert-ack-store";

function subscribe(callback: () => void): () => void {
  const handler = () => callback();
  window.addEventListener("storage", handler);
  window.addEventListener("aerovantage-alert-acks-changed", handler);
  return () => {
    window.removeEventListener("storage", handler);
    window.removeEventListener("aerovantage-alert-acks-changed", handler);
  };
}

const EMPTY_ACKS: Record<string, AlertAckRecord> = {};

export function useAlertAcks() {
  const acks = useSyncExternalStore(subscribe, getAlertAcks, () => EMPTY_ACKS);

  const ack = useCallback((alertId: string) => {
    acknowledgeAlert(alertId);
  }, []);

  const unack = useCallback((alertId: string) => {
    clearAlertAck(alertId);
  }, []);

  const isAcked = useCallback((alertId: string) => Boolean(acks[alertId]), [acks]);

  return { acks, ack, unack, isAcked };
}
