"use client";

import { RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { OpsPageHeader } from "@/components/ops/ops-page-header";
import { OpsPanel } from "@/components/ops/ops-panel";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorBanner, LoadingBlock } from "@/components/ui/async-state";
import { useOperasyon } from "@/context/operasyon-context";
import { useTranslations } from "@/context/locale-context";
import { fetchPipelineHistory, type PipelineHistoryEntry } from "@/lib/api";
import { formatCurrencyTl, formatDateTime } from "@/lib/format";
import { operationalStatusFromRisk } from "@/lib/status-level";
import { getErrorMessage } from "@/lib/user-messages";
import { cn } from "@/lib/utils";

function formatDate(value?: string): string {
  if (!value) return "—";
  return formatDateTime(value);
}

const SEV_COLOR = {
  ok: "text-zinc-300",
  warn: "text-amber-400",
  crit: "text-rose-400",
};

export default function ActivityPage() {
  const { selectedAssetId } = useOperasyon();
  const { t } = useTranslations("ui");
  const [history, setHistory] = useState<PipelineHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setHistory(await fetchPipelineHistory(30));
    } catch (err) {
      setError(getErrorMessage(err, t("activity.loadFailed")));
      setHistory([]);
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  const filtered = selectedAssetId
    ? history.filter((e) => e.asset_id === selectedAssetId)
    : history;

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      <OpsPageHeader
        section={t("activity.section")}
        title={t("activity.title")}
        description={
          selectedAssetId
            ? t("activity.filterAsset", { asset: selectedAssetId })
            : t("activity.allPlants")
        }
        actions={
          <Button
            variant="ghost"
            size="sm"
            className="h-7 rounded-none border border-[#27272A] px-2 text-[10px] hover:bg-[#18181B]"
            onClick={() => void loadHistory()}
            disabled={loading}
          >
            <RefreshCw className={cn("mr-1 h-3 w-3", loading && "animate-spin")} />
            {t("activity.refresh")}
          </Button>
        }
      />

      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {error ? <ErrorBanner message={error} onRetry={() => void loadHistory()} className="mb-2" /> : null}

        {loading ? <LoadingBlock label={t("activity.loading")} rows={6} /> : null}

        {!loading && filtered.length === 0 ? (
          <EmptyState title={t("activity.emptyTitle")} message={t("activity.emptyMessage")} />
        ) : null}

        {!loading && filtered.length > 0 ? (
          <div className="space-y-1">
            {filtered.map((entry, index) => {
              const risk = entry.risk_score ?? 0;
              const sev = operationalStatusFromRisk(risk);
              return (
                <OpsPanel
                  key={`${entry.saved_at}-${index}`}
                  title={entry.asset_name ?? entry.asset_id ?? t("activity.unknown")}
                  meta={formatDate(entry.saved_at)}
                >
                  <div className="grid grid-cols-4 gap-2">
                    <Metric label={t("activity.risk")} value={String(entry.risk_score ?? "—")} className={SEV_COLOR[sev]} />
                    <Metric
                      label={t("activity.mape")}
                      value={entry.mape_percentage != null ? `%${entry.mape_percentage}` : "—"}
                    />
                    <Metric
                      label={t("activity.cost")}
                      value={
                        entry.total_imbalance_cost_tl != null ? formatCurrencyTl(entry.total_imbalance_cost_tl) : "—"
                      }
                    />
                    <Metric label={t("activity.alert")} value={entry.alert_status?.severity ?? t("status.normal")} />
                  </div>
                  {entry.ai_insight ? (
                    <p className="mt-2 border-t border-[#27272A] pt-2 font-mono text-[10px] leading-relaxed text-zinc-500">
                      {entry.ai_insight}
                    </p>
                  ) : null}
                </OpsPanel>
              );
            })}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function Metric({ label, value, className }: { label: string; value: string; className?: string }) {
  return (
    <div>
      <p className="text-[9px] uppercase text-zinc-600">{label}</p>
      <p className={cn("font-mono text-[11px] text-zinc-300", className)}>{value}</p>
    </div>
  );
}
