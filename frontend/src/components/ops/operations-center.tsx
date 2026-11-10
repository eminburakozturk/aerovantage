"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { PriorityAlertsTable } from "@/components/ops/dashboard/priority-alerts-table";
import { ProductionChart } from "@/components/ops/dashboard/production-chart";
import { SystemHealthPanel } from "@/components/ops/dashboard/system-health-panel";
import { TimelineFeed } from "@/components/ops/dashboard/timeline-feed";
import { AnnotatedKpiCell } from "@/components/ai/annotated-kpi-cell";
import { AnnotationsProvider } from "@/components/ai/annotations-context";
import { ErrorBanner } from "@/components/ui/async-state";
import { useOperasyon } from "@/context/operasyon-context";
import { useTranslations, useLocale } from "@/context/locale-context";
import { formatMape, formatTimeShort } from "@/lib/format";
import { AUTO_DASHBOARD_REFRESH_MS } from "@/lib/live-refresh";
import { PIPELINE_LAG_THRESHOLD_MS } from "@/lib/pipeline-feed-state";
import {
  type DashboardData,
  type HealthResponse,
  type PipelineHistoryEntry,
  fetchHealth,
  fetchLiveDashboard,
  fetchPipelineHistory,
} from "@/lib/api";
import { operationalStatusFromRisk } from "@/lib/status-level";
import { getErrorMessage } from "@/lib/user-messages";

export function OperationsCenter() {
  const {
    assets,
    selectedAssetId,
    assetsLoading,
    setNotifications,
    setSystemStatus,
    setPipelineFeedState,
    touchDataSync,
    lastDataSyncAt,
    pipelineRunning,
    pipelineEpoch,
    pipelineError,
    clearPipelineError,
    setScadaIsMock,
    scadaIsMock,
  } = useOperasyon();

  const [data, setData] = useState<DashboardData | null>(null);
  const [history, setHistory] = useState<PipelineHistoryEntry[]>([]);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string>("—");

  const { t: tm } = useTranslations("monitoring");
  const { locale, localeReady } = useLocale();

  const portfolioIds = useMemo(() => assets.map((a) => a.id), [assets]);
  const loadGenRef = useRef(0);

  const resolveStatus = useCallback(
    (riskScore: number, scadaMock: boolean): "ok" | "warn" | "crit" => {
      const fromRisk = operationalStatusFromRisk(riskScore);
      // SCADA mock iken canlı tahmin sapması "kritik arıza" gibi görünmesin
      if (scadaMock && fromRisk === "crit") return "warn";
      return fromRisk;
    },
    [],
  );

  const applyDashboard = useCallback(
    (dashboard: DashboardData, scadaMock: boolean) => {
      setData(dashboard);
      setNotifications(dashboard.notifications);
      setLastUpdated(formatTimeShort(new Date()));
      touchDataSync();
      setPipelineFeedState("synced");
      setSystemStatus(resolveStatus(dashboard.riskScore, scadaMock));
    },
    [setNotifications, setSystemStatus, touchDataSync, setPipelineFeedState, resolveStatus],
  );

  const loadLiveData = useCallback(async () => {
    if (!selectedAssetId || !localeReady) return;

    const loadGen = ++loadGenRef.current;
    setLoading(true);
    setError(null);

    try {
      const settled = await Promise.allSettled([
        fetchLiveDashboard(selectedAssetId, portfolioIds, 30, locale),
        fetchPipelineHistory(50, locale),
        fetchHealth(),
      ]);

      if (loadGen !== loadGenRef.current) return;

      const dashboardResult = settled[0].status === "fulfilled" ? settled[0].value : null;
      const historyResult = settled[1].status === "fulfilled" ? settled[1].value : [];
      const healthResult = settled[2].status === "fulfilled" ? settled[2].value : null;

      if (healthResult) {
        const scadaHub = healthResult.data_hub?.scada;
        const scadaSimulated =
          scadaHub?.mode === "mock" ||
          scadaHub?.mode === "simulated" ||
          scadaHub?.source === "simulated_from_epias";
        setScadaIsMock(scadaSimulated);
        setHealth(healthResult);
        if (dashboardResult) {
          applyDashboard(dashboardResult, scadaSimulated);
        }
      } else if (dashboardResult) {
        applyDashboard(dashboardResult, true);
      }

      setHistory(historyResult);

      const failures = settled.filter((item) => item.status === "rejected");
      if (failures.length === settled.length) {
        const first = failures[0] as PromiseRejectedResult;
        setError(getErrorMessage(first.reason, tm("loadFailed")));
        setData(null);
        setNotifications([]);
        setSystemStatus("crit");
        setPipelineFeedState("offline");
      } else if (failures.length > 0) {
        setError(getErrorMessage((failures[0] as PromiseRejectedResult).reason, tm("partialLoad")));
        setPipelineFeedState("lag");
      } else {
        setError(null);
      }
    } catch (err) {
      if (loadGen !== loadGenRef.current) return;
      setError(getErrorMessage(err, tm("loadFailed")));
      // Son iyi veriyi silme — boş KPI / Warte auf Backend önlenir
      setSystemStatus("crit");
      setPipelineFeedState("offline");
    } finally {
      if (loadGen === loadGenRef.current) {
        setLoading(false);
      }
    }
  }, [
    selectedAssetId,
    portfolioIds,
    applyDashboard,
    setNotifications,
    setSystemStatus,
    setPipelineFeedState,
    setScadaIsMock,
    tm,
    locale,
    localeReady,
  ]);

  useEffect(() => {
    const checkLag = () => {
      if (pipelineRunning || !lastDataSyncAt) return;
      if (Date.now() - lastDataSyncAt > PIPELINE_LAG_THRESHOLD_MS) {
        setPipelineFeedState((current) =>
          current === "running" || current === "offline" ? current : "lag",
        );
      }
    };

    checkLag();
    const id = setInterval(checkLag, 30_000);
    return () => clearInterval(id);
  }, [lastDataSyncAt, pipelineRunning, setPipelineFeedState]);

  useEffect(() => {
    if (!localeReady || assetsLoading || !selectedAssetId || portfolioIds.length === 0) return;
    void loadLiveData();
  }, [localeReady, assetsLoading, selectedAssetId, portfolioIds.length, loadLiveData, locale]);

  // Global pipeline tamamlanınca dashboard'u yenile
  useEffect(() => {
    if (!localeReady || pipelineEpoch === 0 || assetsLoading || !selectedAssetId) return;
    void loadLiveData();
  }, [pipelineEpoch]); // eslint-disable-line react-hooks/exhaustive-deps

  // Hafif yenileme: health + son history (10 dk) — EPİAŞ saatlik pipeline'dan bağımsız
  useEffect(() => {
    if (!localeReady || assetsLoading || !selectedAssetId) return;
    const id = window.setInterval(() => {
      if (pipelineRunning) return;
      if (typeof document !== "undefined" && document.visibilityState === "hidden") return;
      void loadLiveData();
    }, AUTO_DASHBOARD_REFRESH_MS);
    return () => window.clearInterval(id);
  }, [localeReady, assetsLoading, selectedAssetId, pipelineRunning, loadLiveData]);

  const displayError = pipelineError ?? error;

  const lastHour = data?.hourlyProduction?.[data.hourlyProduction.length - 1];
  const actualMw = lastHour?.actual_mw ?? data?.forecastMw ?? 0;
  const forecastMw = data?.forecastMw ?? 0;
  const productionDelta =
    forecastMw > 0 ? ((actualMw - forecastMw) / forecastMw) * 100 : null;
  const deltaLabel =
    productionDelta !== null
      ? `${productionDelta >= 0 ? "▲" : "▼"} ${productionDelta >= 0 ? "+" : ""}${productionDelta.toFixed(1)}%`
      : undefined;

  const riskStatus = !data
    ? "neutral"
    : scadaIsMock
      ? "neutral"
      : resolveStatus(data.riskScore, false);
  const mapeStatus = !data
    ? "neutral"
    : scadaIsMock
      ? "neutral"
      : data.liveMapePercentage > 18
        ? "crit"
        : data.liveMapePercentage > 15
          ? "warn"
          : "neutral";
  const alertStatus = !data
    ? "neutral"
    : scadaIsMock
      ? "neutral"
      : data.criticalAlertsCount > 0
        ? "crit"
        : "neutral";
  const costStatus =
    !data || scadaIsMock
      ? "neutral"
      : data.totalImbalanceCostTl > 100000
        ? "warn"
        : "neutral";

  const productionTrend = useMemo(
    () => (data?.hourlyProduction ?? []).map((h) => h.actual_mw ?? h.forecast_mw ?? 0),
    [data?.hourlyProduction],
  );
  const forecastTrend = useMemo(
    () => (data?.hourlyProduction ?? []).map((h) => h.forecast_mw ?? 0),
    [data?.hourlyProduction],
  );
  const mapeTrend = useMemo(
    () => [...history].reverse().slice(-8).map((h) => h.mape_percentage ?? 0),
    [history],
  );
  const riskTrend = useMemo(
    () => [...history].reverse().slice(-8).map((h) => h.risk_score ?? 0),
    [history],
  );
  const costTrend = useMemo(
    () => [...history].reverse().slice(-8).map((h) => h.total_imbalance_cost_tl ?? 0),
    [history],
  );

  return (
    <AnnotationsProvider context="operations">
      <div className="flex h-full min-h-0 overflow-hidden bg-[#09090B]">
        <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-1.5 overflow-y-auto p-1.5 lg:p-2">
          <section className="grid shrink-0 grid-cols-2 gap-1 md:grid-cols-3 xl:grid-cols-6">
            <AnnotatedKpiCell
              kpiId="production"
              label={tm("kpi.production")}
              value={loading || pipelineRunning ? "—" : actualMw.toFixed(1)}
              unit="MW"
              sub={data?.assetName ?? data?.assetId}
              delta={deltaLabel}
              deltaPositive={productionDelta !== null ? productionDelta >= 0 : undefined}
              updatedAt={lastUpdated}
              trend={productionTrend}
              status="neutral"
              compact
            />
            <AnnotatedKpiCell
              kpiId="forecast"
              label={tm("kpi.forecast")}
              value={loading || pipelineRunning ? "—" : forecastMw.toFixed(1)}
              unit="MW"
              sub={data?.targetDate}
              updatedAt={lastUpdated}
              trend={forecastTrend}
              compact
            />
            <AnnotatedKpiCell
              kpiId="imbalance_cost"
              label={tm("kpi.cost")}
              value={loading || pipelineRunning ? "—" : ""}
              unit="TL"
              compactCurrency={data?.totalImbalanceCostTl}
              status={costStatus}
              updatedAt={lastUpdated}
              trend={costTrend}
              compact
            />
            <AnnotatedKpiCell
              kpiId="live_mape"
              label={tm("kpi.liveMape")}
              value={loading || pipelineRunning ? "—" : formatMape(data?.liveMapePercentage)}
              unit="%"
              sub={data ? tm("kpi.periodMape", { value: formatMape(data.averageMape) }) : undefined}
              status={mapeStatus as "ok" | "warn" | "crit" | "neutral"}
              updatedAt={lastUpdated}
              trend={mapeTrend}
              compact
            />
            <AnnotatedKpiCell
              kpiId="risk"
              label={tm("kpi.risk")}
              value={loading || pipelineRunning ? "—" : String(data?.riskScore ?? "—")}
              unit="/100"
              status={riskStatus as "ok" | "warn" | "crit" | "neutral"}
              updatedAt={lastUpdated}
              trend={riskTrend}
              emphasis
              compact
            />
            <AnnotatedKpiCell
              kpiId="critical_alerts"
              label={tm("kpi.alerts")}
              value={loading || pipelineRunning ? "—" : String(data?.criticalAlertsCount ?? 0)}
              status={alertStatus as "ok" | "warn" | "crit" | "neutral"}
              updatedAt={lastUpdated}
              emphasis
              compact
            />
          </section>

        {scadaIsMock ? (
          <div className="shrink-0 border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-[11px] text-amber-200/90">
            {tm("scadaMockBanner")}
          </div>
        ) : null}

        {displayError ? (
          <ErrorBanner
            message={displayError}
            onRetry={() => {
              clearPipelineError();
              void loadLiveData();
            }}
            className="shrink-0"
          />
        ) : null}

        <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-hidden">
          <section className="grid h-[min(36vh,320px)] shrink-0 grid-cols-1 gap-1.5 overflow-hidden lg:grid-cols-2">
            <ProductionChart data={data} compact className="h-full min-h-0" />
            <PriorityAlertsTable data={data} className="h-full min-h-0" />
          </section>

          <section className="grid h-[min(28vh,240px)] min-h-0 shrink-0 grid-cols-1 gap-1.5 overflow-hidden md:grid-cols-2">
            <TimelineFeed history={history} data={data} className="h-full min-h-0 overflow-hidden" />
            <SystemHealthPanel health={health} loading={loading || pipelineRunning} className="h-full min-h-0 overflow-hidden" />
          </section>
        </div>
      </div>
      </div>
    </AnnotationsProvider>
  );
}
