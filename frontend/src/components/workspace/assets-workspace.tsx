"use client";

import { useEffect, useState } from "react";

import { EmptyState, ErrorBanner, LoadingBlock } from "@/components/ui/async-state";
import { useOperasyon } from "@/context/operasyon-context";
import { useTranslations } from "@/context/locale-context";
import type { PipelineHistoryEntry, Turbine } from "@/lib/api";
import { fetchTurbines } from "@/lib/api";
import { dedupeHistoryByAssetDate } from "@/lib/history-utils";
import { operationalStatusFromRisk, STATUS_COLORS } from "@/lib/status-level";
import { getErrorMessage, statusLabel } from "@/lib/user-messages";
import { cn } from "@/lib/utils";

import { KpiCell } from "@/components/ops/kpi-cell";
import { OpsPanel } from "@/components/ops/ops-panel";

interface AssetsWorkspaceProps {
  tab: string;
  history: PipelineHistoryEntry[];
}

export function AssetsWorkspace({ tab, history }: AssetsWorkspaceProps) {
  const { assets, assetsLoading, assetsError } = useOperasyon();

  switch (tab) {
    case "turbines":
      return <TurbinesTab />;
    case "health":
      return <HealthTab assets={assets} history={history} loading={assetsLoading} />;
    case "performance":
      return <PerformanceTab assets={assets} history={history} loading={assetsLoading} />;
    default:
      return <PlantsTab assets={assets} loading={assetsLoading} error={assetsError} />;
  }
}

function TurbinesTab() {
  const { selectedAssetId } = useOperasyon();
  const { t } = useTranslations("ui");
  const [turbines, setTurbines] = useState<Turbine[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedAssetId) {
      setTurbines([]);
      setLoading(false);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    void fetchTurbines(selectedAssetId)
      .then(setTurbines)
      .catch((err) => {
        setTurbines([]);
        setError(getErrorMessage(err, t("assets.turbineInventory")));
      })
      .finally(() => setLoading(false));
  }, [selectedAssetId, t]);

  if (!selectedAssetId) {
    return (
      <EmptyState
        title={t("assets.selectPlant")}
        message={t("assets.selectPlantMessage")}
      />
    );
  }

  return (
    <OpsPanel title={t("assets.turbineInventory")} meta={t("assets.turbineCountMeta", { count: turbines.length })} density="comfortable">
      {error ? <ErrorBanner message={error} className="mb-3" /> : null}
      {loading ? <LoadingBlock label={t("assets.turbineInventory")} rows={3} /> : null}
      {!loading ? (
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {turbines.map((t2) => (
            <div key={t2.id} className="ops-surface-interactive p-3">
              <p className="text-[11px] font-medium text-zinc-200">{t2.id}</p>
              <p className="text-[10px] text-zinc-500">{t2.model}</p>
              <div className="mt-2 flex justify-between text-[10px]">
                <span className="text-zinc-600">{t2.capacity_mw} MW</span>
                <span className={cn(t2.status === "operational" ? "text-zinc-400" : "text-amber-400")}>
                  {statusLabel(t2.status)}
                </span>
                <span className="font-mono text-zinc-500">{t2.health_score}</span>
              </div>
            </div>
          ))}
        </div>
      ) : null}
      {!loading && !error && turbines.length === 0 ? (
        <EmptyState
          title={t("assets.noTurbineRecords")}
          message={t("assets.noTurbineDataMessage")}
          className="mt-3"
        />
      ) : null}
    </OpsPanel>
  );
}

function PlantsTab({
  assets,
  loading,
  error,
}: {
  assets: ReturnType<typeof useOperasyon>["assets"];
  loading: boolean;
  error: string | null;
}) {
  const { t } = useTranslations("ui");
  if (error) return <ErrorBanner message={error} className="mb-2" />;

  return (
    <div className="space-y-2">
      <section className="grid grid-cols-3 border border-[#27272A] bg-[#18181B]">
        <KpiCell label={t("risk.plant")} value={loading ? "—" : String(assets.length)} />
        <KpiCell label={t("assets.totalCapacity")} value={loading ? "—" : assets.reduce((s, a) => s + a.capacity_mw, 0).toFixed(1)} unit="MW" />
        <KpiCell label={t("assets.type")} value="RES" />
      </section>

      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {assets.map((asset) => (
          <div key={asset.id} className="ops-surface-interactive p-3">
            <p className="text-[12px] font-medium text-zinc-100">{asset.name}</p>
            <p className="mt-1 font-mono text-[10px] text-zinc-600">{asset.id}</p>
            <div className="mt-3 grid grid-cols-2 gap-2 border-t border-[#27272A] pt-2">
              <Mini label={t("assets.capacity")} value={`${asset.capacity_mw} MW`} />
              <Mini label={t("assets.type")} value={asset.type} />
              <Mini label={t("assets.latitude")} value={asset.lat.toFixed(2)} />
              <Mini label={t("assets.longitude")} value={asset.lon.toFixed(2)} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function HealthTab({
  assets,
  history,
  loading,
}: {
  assets: ReturnType<typeof useOperasyon>["assets"];
  history: PipelineHistoryEntry[];
  loading: boolean;
}) {
  const { t } = useTranslations("ui");
  const latestByAsset = new Map<string, PipelineHistoryEntry>();
  for (const entry of history) {
    if (entry.asset_id && !latestByAsset.has(entry.asset_id)) {
      latestByAsset.set(entry.asset_id, entry);
    }
  }

  return (
    <OpsPanel title={t("assets.assetHealth")} meta={t("assets.fromPipelineRiskMeta")}>
      <div className="space-y-2">
        {assets.map((asset) => {
          const entry = latestByAsset.get(asset.id);
          const risk = entry?.risk_score ?? 0;
          const status = operationalStatusFromRisk(risk);
          return (
            <div key={asset.id} className="flex items-center justify-between border border-[#27272A] p-2">
              <div>
                <p className="text-[11px] text-zinc-200">{asset.name}</p>
                <p className="font-mono text-[9px] text-zinc-600">{asset.id}</p>
              </div>
              <div className="text-right">
                <p className={cn("font-mono text-sm", STATUS_COLORS[status === "ok" ? "normal" : status].text)}>
                  {loading ? "—" : risk}
                </p>
                <p className="text-[9px] text-zinc-600">{t("assets.riskUnit")}</p>
              </div>
            </div>
          );
        })}
      </div>
    </OpsPanel>
  );
}

function PerformanceTab({
  assets,
  history,
  loading,
}: {
  assets: ReturnType<typeof useOperasyon>["assets"];
  history: PipelineHistoryEntry[];
  loading: boolean;
}) {
  const { t } = useTranslations("ui");
  const uniqueHistory = dedupeHistoryByAssetDate(history);
  const perfByAsset = assets.map((asset) => {
    const entries = uniqueHistory.filter((h) => h.asset_id === asset.id);
    const avgMape = entries.length
      ? entries.reduce((s, e) => s + (e.mape_percentage ?? 0), 0) / entries.length
      : null;
    const avgMw = entries.length
      ? entries.reduce((s, e) => s + (e.total_daily_mw ?? 0), 0) / entries.length
      : null;
    return { asset, avgMape, avgMw, records: entries.length };
  });

  return (
    <OpsPanel title={t("assets.performance")} meta={t("assets.fromPipelineHistoryMeta")}>
      <table className="w-full text-[10px]">
        <thead>
          <tr className="border-b border-[#27272A] text-left text-zinc-600">
            <th className="pb-2 pr-3">{t("risk.plant")}</th>
            <th className="pb-2 pr-3">{t("assets.avgMape")}</th>
            <th className="pb-2 pr-3">{t("assets.avgProduction")}</th>
            <th className="pb-2">{t("assets.records")}</th>
          </tr>
        </thead>
        <tbody>
          {perfByAsset.map(({ asset, avgMape, avgMw, records }) => (
            <tr key={asset.id} className="border-b border-[#27272A]/50">
              <td className="py-2 pr-3 text-zinc-300">{asset.name}</td>
              <td className="py-2 pr-3 font-mono text-zinc-400">{loading || avgMape == null ? "—" : `%${avgMape.toFixed(1)}`}</td>
              <td className="py-2 pr-3 font-mono text-zinc-400">{loading || avgMw == null ? "—" : `${avgMw.toFixed(1)} MW`}</td>
              <td className="py-2 font-mono text-zinc-500">{records}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </OpsPanel>
  );
}

function Mini({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[9px] text-zinc-600">{label}</p>
      <p className="font-mono text-[10px] text-zinc-400">{value}</p>
    </div>
  );
}
