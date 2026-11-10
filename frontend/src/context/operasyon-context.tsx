"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import {
  ApiError,
  type Asset,
  type NotificationItem,
  fetchAssets,
  fetchDashboardWithPipeline,
  fetchLiveDashboard,
} from "@/lib/api";
import type { PipelineFeedState } from "@/lib/pipeline-feed-state";
import { AUTO_PIPELINE_INTERVAL_MS } from "@/lib/live-refresh";
import { operationalStatusFromRisk } from "@/lib/status-level";
import { getErrorMessage } from "@/lib/user-messages";
import { useLocale } from "@/context/locale-context";
import { translate } from "@/i18n/get-message";
import { loadMessages } from "@/i18n/load-messages";

interface OperasyonContextValue {
  assets: Asset[];
  selectedAssetId: string;
  setSelectedAssetId: (assetId: string) => void;
  notifications: NotificationItem[];
  setNotifications: (items: NotificationItem[]) => void;
  assetsLoading: boolean;
  assetsError: string | null;
  reloadAssets: () => Promise<void>;
  pipelineRunning: boolean;
  pipelineFeedState: PipelineFeedState;
  setPipelineFeedState: React.Dispatch<React.SetStateAction<PipelineFeedState>>;
  lastDataSyncAt: number | null;
  touchDataSync: () => void;
  /** Pipeline tamamlandığında artar — sayfalar yenileme için dinler. */
  pipelineEpoch: number;
  /** Canlı veri yenile (pipeline çalıştırmadan). Sayfalar pipelineEpoch dinler. */
  refreshLiveData: () => Promise<void>;
  liveRefreshing: boolean;
  pipelineError: string | null;
  clearPipelineError: () => void;
  systemStatus: "ok" | "warn" | "crit" | "idle";
  setSystemStatus: (status: "ok" | "warn" | "crit" | "idle") => void;
  /** SCADA mock iken risk/MAPE kritik görünümü yumuşatılır. */
  scadaIsMock: boolean;
  setScadaIsMock: (value: boolean) => void;
  runPipeline: () => Promise<void>;
}

const OperasyonContext = createContext<OperasyonContextValue | null>(null);

export function OperasyonProvider({ children }: { children: ReactNode }) {
  const { locale, localeReady } = useLocale();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [selectedAssetId, setSelectedAssetId] = useState("");
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [assetsLoading, setAssetsLoading] = useState(true);
  const [assetsError, setAssetsError] = useState<string | null>(null);
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [pipelineFeedState, setPipelineFeedState] = useState<PipelineFeedState>("ready");
  const [lastDataSyncAt, setLastDataSyncAt] = useState<number | null>(null);
  const [pipelineEpoch, setPipelineEpoch] = useState(0);
  const [liveRefreshing, setLiveRefreshing] = useState(false);
  const [pipelineError, setPipelineError] = useState<string | null>(null);
  const [systemStatus, setSystemStatus] = useState<"ok" | "warn" | "crit" | "idle">("idle");
  const [scadaIsMock, setScadaIsMock] = useState(true);
  const runningLockRef = useRef(false);
  const notifyFetchGenRef = useRef(0);

  const touchDataSync = useCallback(() => {
    setLastDataSyncAt(Date.now());
  }, []);

  const clearPipelineError = useCallback(() => {
    setPipelineError(null);
  }, []);

  const runPipeline = useCallback(async () => {
    if (!selectedAssetId || runningLockRef.current || !localeReady) {
      return;
    }
    runningLockRef.current = true;
    setPipelineRunning(true);
    setPipelineFeedState("running");
    setPipelineError(null);
    const fetchGen = ++notifyFetchGenRef.current;

    try {
      const portfolioIds = assets.map((asset) => asset.id);
      const dashboard = await fetchDashboardWithPipeline(
        selectedAssetId,
        portfolioIds.length > 0 ? portfolioIds : [selectedAssetId],
        30,
        locale,
      );
      if (fetchGen !== notifyFetchGenRef.current) return;
      setNotifications(dashboard.notifications);
      const fromRisk = operationalStatusFromRisk(dashboard.riskScore);
      setSystemStatus(scadaIsMock && fromRisk === "crit" ? "warn" : fromRisk);
      setPipelineFeedState("synced");
      touchDataSync();
      setPipelineEpoch((value) => value + 1);
    } catch (err) {
      if (fetchGen !== notifyFetchGenRef.current) return;
      const gateFailure = err instanceof ApiError && err.status === 422;
      setPipelineError(getErrorMessage(err));
      setSystemStatus(gateFailure ? "warn" : "crit");
      setPipelineFeedState(gateFailure ? "lag" : "offline");
      // Gate fail olsa bile epoch artırılsın; UI son kayıtlı veriyi yenilesin.
      if (gateFailure) {
        setPipelineEpoch((value) => value + 1);
      }
    } finally {
      setPipelineRunning(false);
      runningLockRef.current = false;
    }
  }, [selectedAssetId, assets, touchDataSync, scadaIsMock, locale, localeReady]);

  const reloadAssets = useCallback(async () => {
    setAssetsLoading(true);
    setAssetsError(null);
    try {
      const loaded = await fetchAssets();
      setAssets(loaded);
      setSelectedAssetId((current) => {
        if (current && loaded.some((asset) => asset.id === current)) {
          return current;
        }
        return loaded[0]?.id ?? "";
      });
    } catch (err) {
      const fallback = translate(loadMessages(locale).ui as never, "activity.assetsLoadFailed");
      setAssetsError(err instanceof Error ? err.message : fallback);
      setAssets([]);
    } finally {
      setAssetsLoading(false);
    }
  }, [locale]);

  const refreshLiveData = useCallback(async () => {
    if (!localeReady || liveRefreshing) return;
    setLiveRefreshing(true);
    try {
      let assetId = selectedAssetId;
      let portfolioIds = assets.map((asset) => asset.id);
      try {
        const loaded = await fetchAssets();
        setAssets(loaded);
        setSelectedAssetId((current) => {
          if (current && loaded.some((asset) => asset.id === current)) {
            assetId = current;
            return current;
          }
          assetId = loaded[0]?.id ?? "";
          return assetId;
        });
        portfolioIds = loaded.map((asset) => asset.id);
      } catch {
        // keep existing assets list
      }

      if (assetId) {
        try {
          const dashboard = await fetchLiveDashboard(
            assetId,
            portfolioIds.length > 0 ? portfolioIds : [assetId],
            30,
            locale,
          );
          setNotifications(dashboard.notifications);
          const fromRisk = operationalStatusFromRisk(dashboard.riskScore);
          setSystemStatus(scadaIsMock && fromRisk === "crit" ? "warn" : fromRisk);
          setPipelineFeedState("synced");
        } catch {
          // Epoch still bumps so pages reload what they can
        }
      }
      touchDataSync();
      setPipelineEpoch((value) => value + 1);
    } finally {
      setLiveRefreshing(false);
    }
  }, [
    localeReady,
    liveRefreshing,
    selectedAssetId,
    assets,
    locale,
    scadaIsMock,
    touchDataSync,
  ]);

  useEffect(() => {
    void reloadAssets();
  }, [reloadAssets]);

  // Dil değişince bildirimleri history üzerinden yeniden çek (pipeline re-run gerekmez)
  useEffect(() => {
    if (!localeReady || !selectedAssetId || assetsLoading) return;

    const fetchGen = ++notifyFetchGenRef.current;
    const portfolioIds = assets.map((asset) => asset.id);

    void (async () => {
      try {
        const dashboard = await fetchLiveDashboard(
          selectedAssetId,
          portfolioIds.length > 0 ? portfolioIds : [selectedAssetId],
          30,
          locale,
        );
        if (fetchGen !== notifyFetchGenRef.current) return;
        setNotifications(dashboard.notifications);
      } catch {
        // Önceki bildirimleri koru
      }
    })();
    // assets intentionally omitted — portfolio id list via selectedAssetId + length gate
    // eslint-disable-next-line react-hooks/exhaustive-deps -- assets map read at effect time
  }, [locale, localeReady, selectedAssetId, assetsLoading, assets.length]);

  // EPİAŞ saatlik taneye hizalı otomatik pipeline (sayfa açıkken)
  useEffect(() => {
    if (!selectedAssetId || assetsLoading || !localeReady) return;

    const id = window.setInterval(() => {
      if (runningLockRef.current) return;
      if (typeof document !== "undefined" && document.visibilityState === "hidden") return;
      void runPipeline();
    }, AUTO_PIPELINE_INTERVAL_MS);

    return () => window.clearInterval(id);
  }, [selectedAssetId, assetsLoading, runPipeline, localeReady]);

  const value = useMemo(
    () => ({
      assets,
      selectedAssetId,
      setSelectedAssetId,
      notifications,
      setNotifications,
      assetsLoading,
      assetsError,
      reloadAssets,
      pipelineRunning,
      pipelineFeedState,
      setPipelineFeedState,
      lastDataSyncAt,
      touchDataSync,
      pipelineEpoch,
      refreshLiveData,
      liveRefreshing,
      pipelineError,
      clearPipelineError,
      systemStatus,
      setSystemStatus,
      scadaIsMock,
      setScadaIsMock,
      runPipeline,
    }),
    [
      assets,
      selectedAssetId,
      notifications,
      assetsLoading,
      assetsError,
      reloadAssets,
      pipelineRunning,
      pipelineFeedState,
      lastDataSyncAt,
      touchDataSync,
      pipelineEpoch,
      refreshLiveData,
      liveRefreshing,
      pipelineError,
      clearPipelineError,
      systemStatus,
      scadaIsMock,
      runPipeline,
    ],
  );

  return <OperasyonContext.Provider value={value}>{children}</OperasyonContext.Provider>;
}

export function useOperasyon() {
  const context = useContext(OperasyonContext);
  if (!context) {
    throw new Error("useOperasyon yalnızca OperasyonProvider içinde kullanılabilir");
  }
  return context;
}
