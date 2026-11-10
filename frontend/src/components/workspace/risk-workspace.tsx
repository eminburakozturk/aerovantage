"use client";

import Link from "next/link";
import { AreaChart } from "@tremor/react";

import { AiInlineHint } from "@/components/ai/ai-inline-hint";
import { AnnotatedKpiCell } from "@/components/ai/annotated-kpi-cell";
import { useAnnotations } from "@/components/ai/annotations-context";
import { KpiCell } from "@/components/ops/kpi-cell";
import { OpsPanel } from "@/components/ops/ops-panel";
import { ErrorBanner } from "@/components/ui/async-state";
import { useOperasyon } from "@/context/operasyon-context";
import { useTranslations } from "@/context/locale-context";
import type { BriefingAnnotation, DashboardData, PipelineHistoryEntry } from "@/lib/api";
import { formatTimeShort } from "@/lib/format";
import { dedupeHistoryByAssetDate, historyTrendRows } from "@/lib/history-utils";
import { cn } from "@/lib/utils";
import {
  levelToKpiStatus,
  normalizeSeverity,
  severityFromRisk,
  STATUS_COLORS,
  type StatusLevel,
} from "@/lib/status-level";

interface RiskWorkspaceProps {
  tab: string;
  data: DashboardData | null;
  history: PipelineHistoryEntry[];
  loading: boolean;
  error: string | null;
}

interface RiskBreakdownRow {
  id: string;
  component: string;
  value: string;
  status: StatusLevel;
  annotation?: BriefingAnnotation;
}

export function RiskWorkspace({ tab, data, history, loading, error }: RiskWorkspaceProps) {
  if (error) return <ErrorBanner message={error} />;

  switch (tab) {
    case "financial":
      return <FinancialTab data={data} loading={loading} />;
    case "production":
      return <ProductionTab data={data} loading={loading} />;
    case "timeline":
      return <TimelineTab history={history} />;
    default:
      return <DashboardTab data={data} loading={loading} />;
  }
}

function buildRiskBreakdown(
  data: DashboardData | null,
  getKpi: (id: string) => BriefingAnnotation | undefined,
  getAlert: (id: string) => BriefingAnnotation | undefined,
  t: (key: string, params?: Record<string, string | number>) => string,
): RiskBreakdownRow[] {
  if (!data) return [];

  const mape = data.liveMapePercentage ?? 0;
  const mapeStatus: StatusLevel = mape >= 20 ? "crit" : mape >= 15 ? "warn" : "normal";
  const cost = data.totalImbalanceCostTl ?? 0;
  const costStatus: StatusLevel = cost > 100000 ? "crit" : cost > 50000 ? "warn" : "normal";

  const rows: RiskBreakdownRow[] = [
    {
      id: "mape",
      component: t("risk.mape"),
      value: `%${mape.toFixed(1)} MAPE`,
      status: mapeStatus,
      annotation: getKpi("live_mape"),
    },
    {
      id: "financial",
      component: t("risk.financial"),
      value: `${cost.toLocaleString("tr-TR")} TL`,
      status: costStatus,
      annotation: getKpi("imbalance_cost"),
    },
    {
      id: "alerts",
      component: t("risk.criticalAlert"),
      value: `${data.criticalAlertsCount ?? 0}`,
      status: (data.criticalAlertsCount ?? 0) > 0 ? "crit" : "normal",
      annotation: getKpi("critical_alerts"),
    },
  ];

  for (const rule of data.rules) {
    const sev = normalizeSeverity(rule.severity);
    rows.push({
      id: `rule-${rule.rule_id}`,
      component: `${t("ops.rule")}: ${rule.rule_id}`,
      value: rule.message,
      status: sev === "unknown" ? "warn" : sev,
      annotation: getAlert(rule.rule_id),
    });
  }

  return rows;
}

function DashboardTab({ data, loading }: { data: DashboardData | null; loading: boolean }) {
  const { t } = useTranslations("ui");
  const { scadaIsMock } = useOperasyon();
  const risk = data?.riskScore ?? 0;
  const { getKpi, getAlert, loading: aiLoading, annotations } = useAnnotations();
  const breakdown = buildRiskBreakdown(data, getKpi, getAlert, t);
  const riskLevel = !data ? "unknown" : scadaIsMock ? "unknown" : severityFromRisk(risk);
  const cost = data?.totalImbalanceCostTl ?? 0;
  const costStatus: "warn" | "neutral" = !data || scadaIsMock ? "neutral" : cost > 100000 ? "warn" : "neutral";
  const mape = data?.liveMapePercentage ?? 0;
  const mapeStatus: "warn" | "neutral" = !data || scadaIsMock ? "neutral" : mape > 15 ? "warn" : "neutral";
  const alertsStatus: "crit" | "neutral" =
    !data || scadaIsMock ? "neutral" : (data?.criticalAlertsCount ?? 0) > 0 ? "crit" : "neutral";
  const topAction = annotations.find((a) => a.recommended_action?.trim())?.recommended_action;
  const showEmphasisBorder = riskLevel === "warn" || riskLevel === "crit";

  return (
    <div className="space-y-2">
      <section
        className={cn(
          "flex flex-wrap items-start justify-between gap-3 border border-[#27272A] bg-[#18181B] px-3 py-2",
          showEmphasisBorder ? "border-l-2 border-l-amber-500/60" : "border-l-2 border-l-[#27272A]",
        )}
      >
        <div>
          <p className="text-[9px] font-semibold uppercase tracking-[0.08em] text-zinc-500">{t("risk.totalRisk")}</p>
          <p className={cn("font-mono text-2xl font-medium tabular-nums", STATUS_COLORS[riskLevel].text)}>
            {loading ? "—" : risk}
            <span className="ml-1 text-sm text-zinc-600">/100</span>
          </p>
        </div>
        <div className="hidden shrink-0 sm:block">
          <RiskGauge score={risk} loading={loading} compact />
        </div>
        <div className="min-w-0 flex-1 sm:max-w-md">
          <AiInlineHint annotation={getKpi("risk")} loading={aiLoading} compact className="border-t-0 pt-0" />
        </div>
      </section>

      <section className="grid grid-cols-2 gap-1 md:grid-cols-4">
        <AnnotatedKpiCell
          kpiId="risk"
          label={t("risk.risk")}
          value={loading ? "—" : String(risk)}
          unit="/100"
          status={levelToKpiStatus(riskLevel)}
        />
        <AnnotatedKpiCell kpiId="imbalance_cost" label={t("risk.financial")} value={loading ? "—" : ""} unit="TL" compactCurrency={data?.totalImbalanceCostTl} status={costStatus} />
        <AnnotatedKpiCell kpiId="critical_alerts" label={t("risk.criticalAlert")} value={loading ? "—" : String(data?.criticalAlertsCount ?? 0)} status={alertsStatus} />
        <AnnotatedKpiCell kpiId="live_mape" label={t("risk.mape")} value={loading ? "—" : (data?.liveMapePercentage.toFixed(1) ?? "—")} unit="%" status={mapeStatus} />
      </section>

      <OpsPanel title={t("risk.riskBreakdown")} meta={t("risk.componentsMeta", { count: breakdown.length })} density="comfortable" className="min-h-[200px]">
        <RiskBreakdownTable rows={breakdown} loading={loading} aiLoading={aiLoading} />
      </OpsPanel>

      <div className="grid gap-2 lg:grid-cols-2">
        <OpsPanel title={t("risk.decisionSupport")} meta={t("risk.recommendedActionMeta")}>
          {topAction ? (
            <>
              <p className="font-mono text-[11px] leading-relaxed text-[#93C5FD]">→ {topAction}</p>
              <Link href="/ai?from=risk" className="mt-2 inline-block text-[10px] text-[#3B82F6] hover:underline">
                {t("risk.approveInDecision")} →
              </Link>
            </>
          ) : (
            <>
              <p className="text-[10px] text-zinc-500">{t("risk.noPendingAction")}</p>
              <Link href="/ai?from=risk" className="mt-2 inline-block text-[10px] text-[#3B82F6] hover:underline">
                {t("risk.decisionCenter")} →
              </Link>
            </>
          )}
        </OpsPanel>

        <OpsPanel title={t("risk.riskTrend")} meta={t("commonUi.secondaryView")}>
          <div className="flex items-center gap-4">
            <RiskGauge score={risk} loading={loading} compact />
            <p className="text-[10px] leading-relaxed text-zinc-500">{t("risk.breakdownHint")}</p>
          </div>
        </OpsPanel>
      </div>
    </div>
  );
}

function RiskBreakdownTable({
  rows,
  loading,
  aiLoading,
}: {
  rows: RiskBreakdownRow[];
  loading: boolean;
  aiLoading: boolean;
}) {
  const { t } = useTranslations("ui");

  if (loading) {
    return <p className="text-[10px] text-zinc-600">{t("risk.breakdownLoading")}</p>;
  }

  if (!rows.length) {
    return <p className="text-[10px] text-zinc-400">{t("risk.noActiveRiskNormal")}</p>;
  }

  return (
    <div className="overflow-auto">
      <table className="w-full text-left text-[10px]">
        <thead className="border-b border-[#27272A] text-[9px] uppercase tracking-wider text-zinc-600">
          <tr>
            <th className="px-2 py-1.5 font-medium">{t("risk.component")}</th>
            <th className="px-2 py-1.5 font-medium">{t("risk.value")}</th>
            <th className="px-2 py-1.5 font-medium">{t("ops.status")}</th>
            <th className="px-2 py-1.5 font-medium">{t("risk.aiComment")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const colors = STATUS_COLORS[row.status];
            return (
              <tr key={row.id} className="border-b border-[#27272A]/60 align-top last:border-0">
                <td className="px-2 py-2 font-medium text-zinc-300">{row.component}</td>
                <td className="px-2 py-2 text-zinc-400">{row.value}</td>
                <td className="px-2 py-2">
                  <span className={cn("font-semibold uppercase", colors.text)}>{t(`status.${row.status}`)}</span>
                </td>
                <td className="px-2 py-2">
                  <AiInlineHint annotation={row.annotation} loading={aiLoading} compact className="border-t-0 pt-0" />
                  {!row.annotation?.insight && !aiLoading ? (
                    <span className="text-zinc-700">—</span>
                  ) : null}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function FinancialTab({ data, loading }: { data: DashboardData | null; loading: boolean }) {
  const { t } = useTranslations("ui");
  const { getKpi, loading: aiLoading } = useAnnotations();
  const hours = data?.hourlyProduction ?? [];
  const costKey = t("risk.costSeries");
  const hourlyCost = hours.map((h) => ({
    saat: formatTimeShort(h.timestamp),
    [costKey]: h.imbalance_cost_tl ?? 0,
  }));
  const cost = data?.totalImbalanceCostTl ?? 0;
  const costStatus: StatusLevel = cost > 100000 ? "crit" : cost > 50000 ? "warn" : "normal";
  const hourlyAvg =
    hourlyCost.length > 0
      ? hourlyCost.reduce((s, h) => s + Number(h[costKey] ?? 0), 0) / hourlyCost.length
      : 0;

  const financialRows: RiskBreakdownRow[] = [
    {
      id: "total-cost",
      component: t("risk.totalImbalance"),
      value: `${cost.toLocaleString("tr-TR")} TL`,
      status: costStatus,
      annotation: getKpi("imbalance_cost"),
    },
    {
      id: "hourly-avg",
      component: t("risk.hourlyAverage"),
      value: hourlyCost.length ? `${hourlyAvg.toFixed(0)} TL` : "—",
      status: costStatus,
    },
    {
      id: "risk-score",
      component: t("risk.riskScoreImpact"),
      value: `${data?.riskScore ?? "—"}/100`,
      status: severityFromRisk(data?.riskScore),
      annotation: getKpi("risk"),
    },
  ];

  return (
    <div className="space-y-2">
      <section className="grid grid-cols-2 gap-1 md:grid-cols-3">
        <AnnotatedKpiCell kpiId="imbalance_cost" label={t("risk.totalCost")} value={loading ? "—" : ""} unit="TL" compactCurrency={data?.totalImbalanceCostTl} status={levelToKpiStatus(costStatus)} />
        <KpiCell label={t("risk.hourlyAvg")} value={loading ? "—" : hourlyCost.length ? hourlyAvg.toFixed(0) : "—"} unit="TL" />
        <AnnotatedKpiCell kpiId="risk" label={t("risk.riskScore")} value={loading ? "—" : String(data?.riskScore ?? "—")} unit="/100" />
      </section>

      <OpsPanel title={t("risk.financialBreakdown")} meta={t("commonUi.primary")} density="comfortable">
        <RiskBreakdownTable rows={financialRows} loading={loading} aiLoading={aiLoading} />
      </OpsPanel>

      <OpsPanel title={t("risk.hourlyImbalance")} meta={t("commonUi.secondaryChart")}>
        {hourlyCost.length > 0 ? (
          <AreaChart className="ops-chart h-[160px]" data={hourlyCost} index="saat" categories={[costKey]} colors={["blue"]} showLegend={false} showYAxis showXAxis />
        ) : (
          <p className="text-[10px] text-zinc-600">{t("risk.costDataRunPipeline")}</p>
        )}
      </OpsPanel>
    </div>
  );
}

function ProductionTab({ data, loading }: { data: DashboardData | null; loading: boolean }) {
  const { t } = useTranslations("ui");
  const { getKpi, loading: aiLoading } = useAnnotations();
  const hours = data?.hourlyProduction ?? [];
  const deviationKey = t("forecast.deviation");
  const deviationRows: RiskBreakdownRow[] = hours
    .map((h, i) => {
      const delta = h.actual_mw - h.forecast_mw;
      const abs = Math.abs(delta);
      return {
        id: `hour-${i}`,
        component: formatTimeShort(h.timestamp),
        value: `${delta >= 0 ? "+" : ""}${delta.toFixed(1)} MW`,
        status: (abs > 8 ? "crit" : abs > 5 ? "warn" : "normal") as StatusLevel,
        annotation: abs > 5 ? getKpi("forecast_deviation") : undefined,
      };
    })
    .filter((r) => r.status !== "normal")
    .slice(0, 12);

  if (!deviationRows.length && data) {
    deviationRows.push({
      id: "summary",
      component: t("forecast.liveMape"),
      value: `%${(data.liveMapePercentage ?? 0).toFixed(1)}`,
      status: (data.liveMapePercentage ?? 0) > 15 ? "warn" : "normal",
      annotation: getKpi("live_mape"),
    });
  }

  return (
    <div className="space-y-2">
      <section className="grid grid-cols-2 gap-1 md:grid-cols-4">
        <AnnotatedKpiCell kpiId="live_mape" label={t("forecast.liveMape")} value={loading ? "—" : (data?.liveMapePercentage.toFixed(1) ?? "—")} unit="%" status={(data?.liveMapePercentage ?? 0) > 15 ? "warn" : "neutral"} />
        <KpiCell label={t("forecast.avgMape")} value={loading ? "—" : (data?.averageMape.toFixed(1) ?? "—")} unit="%" />
        <AnnotatedKpiCell kpiId="forecast" label={t("forecast.forecast")} value={loading ? "—" : (data?.forecastMw.toFixed(1) ?? "—")} unit="MW" />
        <AnnotatedKpiCell kpiId="forecast_deviation" label={t("risk.deviationHours")} value={loading ? "—" : String(hours.filter((h) => Math.abs(h.actual_mw - h.forecast_mw) > 3).length)} />
      </section>

      <OpsPanel title={t("risk.productionDeviationBreakdown")} meta={t("risk.hourlyPrimaryMeta")} density="comfortable">
        <RiskBreakdownTable rows={deviationRows} loading={loading} aiLoading={aiLoading} />
      </OpsPanel>

      <OpsPanel title={t("risk.deviationChart")} meta={t("commonUi.secondary")}>
        {hours.length > 0 ? (
          <AreaChart
            className="ops-chart h-[140px]"
            data={hours.map((h) => ({
              saat: formatTimeShort(h.timestamp),
              [deviationKey]: Math.abs(h.actual_mw - h.forecast_mw),
            }))}
            index="saat"
            categories={[deviationKey]}
            colors={["slate"]}
            showLegend={false}
            showYAxis
            showXAxis
          />
        ) : (
          <p className="text-[10px] text-zinc-600">{t("risk.noProductionData")}</p>
        )}
      </OpsPanel>
    </div>
  );
}

function TimelineTab({ history }: { history: PipelineHistoryEntry[] }) {
  const { t } = useTranslations("ui");
  const unique = dedupeHistoryByAssetDate(history);
  const timeline = historyTrendRows(unique, 15).map((row) => ({
    tarih: row.tarih,
    Risk: row.Risk,
    MAPE: row.MAPE,
  }));

  return (
    <div className="space-y-2">
      <OpsPanel title={t("risk.recordDetail")} meta={t("risk.pipelineUniqueDayMeta")}>
        <table className="w-full text-[10px]">
          <thead>
            <tr className="border-b border-[#27272A] text-left text-zinc-600">
              <th className="pb-1 pr-3">{t("forecast.date")}</th>
              <th className="pb-1 pr-3">{t("risk.plant")}</th>
              <th className="pb-1 pr-3">{t("risk.risk")}</th>
              <th className="pb-1">{t("forecast.mape")}</th>
            </tr>
          </thead>
          <tbody>
            {unique.slice(0, 10).map((entry, i) => {
              const risk = entry.risk_score ?? 0;
              const sev = STATUS_COLORS[severityFromRisk(risk)].text;
              return (
                <tr key={i} className="border-b border-[#27272A]/50">
                  <td className="py-1.5 pr-3 font-mono text-zinc-500">{entry.target_date}</td>
                  <td className="py-1.5 pr-3 text-zinc-400">{entry.asset_id}</td>
                  <td className={cn("py-1.5 pr-3 font-mono", sev)}>{risk}</td>
                  <td className="py-1.5 font-mono text-zinc-500">%{entry.mape_percentage?.toFixed(1) ?? "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </OpsPanel>

      <OpsPanel title={t("risk.riskTrend")} meta={t("commonUi.secondaryChart")}>
        {timeline.length > 0 ? (
          <AreaChart className="ops-chart h-[140px]" data={timeline} index="tarih" categories={["Risk"]} colors={["blue"]} showLegend={false} showYAxis showXAxis />
        ) : (
          <p className="text-[10px] text-zinc-600">{t("risk.noTimelineData")}</p>
        )}
      </OpsPanel>
    </div>
  );
}

function RiskGauge({ score, loading, compact }: { score: number; loading: boolean; compact?: boolean }) {
  const color = STATUS_COLORS[severityFromRisk(score)].text;
  return (
    <div className="text-center">
      <span className={cn("font-mono font-medium tabular-nums", compact ? "text-2xl" : "text-4xl", color)}>
        {loading ? "—" : score}
      </span>
      <span className="block font-mono text-[10px] text-zinc-600">/100</span>
    </div>
  );
}
