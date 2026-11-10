"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useOperasyon } from "@/context/operasyon-context";
import { useLocale } from "@/context/locale-context";
import {
  type DashboardData,
  type HealthResponse,
  type PipelineHistoryEntry,
  type SystemKpiResponse,
  fetchHealth,
  fetchLiveDashboard,
  fetchPipelineHistory,
  fetchSystemKpi,
} from "@/lib/api";
import { dedupeHistoryByAssetDate } from "@/lib/history-utils";
import { operationalStatusFromRisk } from "@/lib/status-level";
import { getErrorMessage } from "@/lib/user-messages";

export function useWorkspaceData() {
  const {
    assets,
    selectedAssetId,
    assetsLoading,
    setNotifications,
    setSystemStatus,
    pipelineEpoch,
  } = useOperasyon();
  const { locale, localeReady } = useLocale();

  const portfolioIds = useMemo(() => assets.map((a) => a.id), [assets]);
  const [data, setData] = useState<DashboardData | null>(null);
  const [history, setHistory] = useState<PipelineHistoryEntry[]>([]);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [kpi, setKpi] = useState<SystemKpiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const loadGenRef = useRef(0);

  const reload = useCallback(async () => {
    if (!selectedAssetId || !localeReady) return;

    const loadGen = ++loadGenRef.current;
    setLoading(true);
    setError(null);

    try {
      const settled = await Promise.allSettled([
        fetchLiveDashboard(selectedAssetId, portfolioIds, 30, locale),
        fetchPipelineHistory(80, locale),
        fetchHealth(),
        fetchSystemKpi(30),
      ]);

      if (loadGen !== loadGenRef.current) return;

      const dashboard = settled[0].status === "fulfilled" ? settled[0].value : null;
      const hist = settled[1].status === "fulfilled" ? dedupeHistoryByAssetDate(settled[1].value) : [];
      const healthResult = settled[2].status === "fulfilled" ? settled[2].value : null;
      const kpiResult = settled[3].status === "fulfilled" ? settled[3].value : null;

      if (dashboard) {
        setData(dashboard);
        setNotifications(dashboard.notifications);
        setSystemStatus(operationalStatusFromRisk(dashboard.riskScore));
      }
      setHistory(hist);
      if (healthResult) setHealth(healthResult);
      if (kpiResult) setKpi(kpiResult);

      const failures = settled.filter((item) => item.status === "rejected");
      if (failures.length === settled.length) {
        setError(getErrorMessage((failures[0] as PromiseRejectedResult).reason, "Veri yüklenemedi"));
        setSystemStatus("crit");
      } else if (failures.length > 0) {
        setError(getErrorMessage((failures[0] as PromiseRejectedResult).reason, "Kısmi veri yüklendi"));
      } else {
        setError(null);
      }
    } catch (err) {
      if (loadGen !== loadGenRef.current) return;
      setError(getErrorMessage(err, "Veri yüklenemedi"));
      setSystemStatus("crit");
    } finally {
      if (loadGen === loadGenRef.current) {
        setLoading(false);
      }
    }
  }, [selectedAssetId, portfolioIds, setNotifications, setSystemStatus, locale, localeReady]);

  useEffect(() => {
    if (!localeReady || assetsLoading || !selectedAssetId || portfolioIds.length === 0) return;
    void reload();
  }, [localeReady, assetsLoading, selectedAssetId, portfolioIds.length, reload, locale, pipelineEpoch]);

  return { data, history, health, kpi, loading, error, reload, portfolioIds, selectedAssetId };
}
