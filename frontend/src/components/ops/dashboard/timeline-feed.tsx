"use client";

import { OpsPanel } from "@/components/ops/ops-panel";
import { useNavConfig } from "@/hooks/use-nav-config";
import { useLocale, useTranslations } from "@/context/locale-context";
import type { DashboardData, PipelineHistoryEntry } from "@/lib/api";
import { formatCurrencyCompact, formatTimeShort } from "@/lib/format";
import {
  normalizeSeverity,
  severityFromRisk,
  STATUS_COLORS,
  type StatusLevel,
} from "@/lib/status-level";
import { cn } from "@/lib/utils";

interface TimelineFeedProps {
  history: PipelineHistoryEntry[];
  data: DashboardData | null;
  className?: string;
}

function severityFromEntry(entry: PipelineHistoryEntry): StatusLevel {
  const fromAlert = normalizeSeverity(entry.alert_status?.severity);
  if (fromAlert !== "unknown") return fromAlert;
  return severityFromRisk(entry.risk_score);
}

export function TimelineFeed({ history, data, className }: TimelineFeedProps) {
  const { formatStep } = useNavConfig();
  const { t } = useTranslations("ui");
  const { locale } = useLocale();

  const events = history.slice(0, 6).map((entry) => {
    const cost = formatCurrencyCompact(entry.total_imbalance_cost_tl ?? 0).display;
    const localizedSub = t("ops.pipelineEventSummary", {
      risk: entry.risk_score ?? "—",
      mape: entry.mape_percentage != null ? entry.mape_percentage.toFixed(1) : "—",
      cost,
    });
    const rawInsight = entry.ai_insight?.slice(0, 80);
    const sub =
      locale === "tr" && rawInsight
        ? rawInsight
        : localizedSub;
    return {
      id: `${entry.saved_at}-${entry.asset_id}`,
      time: entry.saved_at ? formatTimeShort(entry.saved_at) : "—",
      asset: entry.asset_name ?? entry.asset_id,
      stage: t("commonUi.pipeline"),
      sub,
      severity: severityFromEntry(entry),
    };
  });

  if (data?.stepsCompleted && data.stepsCompleted.length > 0) {
    const latest = data.stepsCompleted[data.stepsCompleted.length - 1];
    events.unshift({
      id: "current",
      time: formatTimeShort(new Date()),
      asset: data.assetName,
      stage: t("ops.live"),
      sub: formatStep(latest ?? ""),
      severity: severityFromRisk(data.riskScore),
    });
  }

  const visible = events.slice(0, 6);

  return (
    <OpsPanel
      title={t("ops.opsFlow")}
      meta={t("ops.recentEventsMeta", { count: visible.length })}
      density="comfortable"
      className={cn("h-full overflow-hidden", className)}
    >
      {visible.length === 0 ? (
        <p className="text-[11px] text-zinc-600">{t("ops.noRecordsRunPipeline")}</p>
      ) : (
        <ul className="flex h-full min-h-0 flex-col gap-0 overflow-y-auto">
          {visible.map((event) => {
            const colors = STATUS_COLORS[event.severity];
            return (
              <li
                key={event.id}
                className="flex gap-2.5 border-b border-[#27272A] py-2.5 last:border-b-0"
              >
                <span
                  className={cn(
                    "mt-0.5 flex w-20 shrink-0 items-center gap-1 font-mono text-[8px] font-bold uppercase tracking-wide",
                    colors.text,
                  )}
                >
                  <span className={cn("h-2 w-2 shrink-0 rounded-full", colors.dot)} aria-hidden />
                  {t(`status.${event.severity}`)}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="font-mono text-[10px] tabular-nums text-zinc-400">{event.time}</p>
                  <p className="mt-0.5 truncate text-[11px] font-medium text-zinc-200">{event.asset}</p>
                  <p className="font-mono text-[9px] uppercase tracking-[0.08em] text-zinc-600">{event.stage}</p>
                  <p className="mt-0.5 line-clamp-2 text-[10px] leading-relaxed text-zinc-500">
                    {event.sub}
                  </p>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </OpsPanel>
  );
}
