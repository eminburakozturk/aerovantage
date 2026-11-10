"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useEffect, useState } from "react";

import { AiInlineHint } from "@/components/ai/ai-inline-hint";
import { AnnotatedKpiCell } from "@/components/ai/annotated-kpi-cell";
import { AnnotationsProvider, useAnnotations } from "@/components/ai/annotations-context";
import { OpsPanel } from "@/components/ops/ops-panel";
import { ErrorBanner } from "@/components/ui/async-state";
import { useTranslations, useLocale } from "@/context/locale-context";
import { useWorkspaceData } from "@/hooks/use-workspace-data";
import { fetchExecutiveReport, type BriefingAnnotation, type ExecutiveReportResponse } from "@/lib/api";
import { formatCurrencyCompact, formatCurrencyTl, formatMape, formatTimeShort } from "@/lib/format";
import { localizeRule } from "@/lib/localize-rules";
import {
  emphasisBorderClass,
  levelToKpiStatus,
  resolveKpiBorderLevel,
  severityFromRisk,
  STATUS_COLORS,
  type StatusLevel,
} from "@/lib/status-level";
import { cn } from "@/lib/utils";
import { APP_ROUTES } from "@/lib/routes";
import { WORKSPACE_IDS, WORKSPACES } from "@/lib/workspace-config";
import { useOperasyon } from "@/context/operasyon-context";

export default function ExecutiveDashboard() {
  const { data, health, loading, error, selectedAssetId } = useWorkspaceData();
  const { locale } = useLocale();
  const [report, setReport] = useState<ExecutiveReportResponse | null>(null);
  const [lastUpdated, setLastUpdated] = useState("—");

  useEffect(() => {
    if (data) setLastUpdated(formatTimeShort(new Date()));
  }, [data]);

  useEffect(() => {
    if (!selectedAssetId) return;
    void fetchExecutiveReport(selectedAssetId, 7, locale)
      .then(setReport)
      .catch(() => setReport(null));
  }, [selectedAssetId, locale]);

  return (
    <AnnotationsProvider context="dashboard">
      <ExecutiveDashboardBody
        data={data}
        health={health}
        loading={loading}
        error={error}
        report={report}
        lastUpdated={lastUpdated}
      />
    </AnnotationsProvider>
  );
}

function ExecutiveDashboardBody({
  data,
  health,
  loading,
  error,
  report,
  lastUpdated,
}: {
  data: ReturnType<typeof useWorkspaceData>["data"];
  health: ReturnType<typeof useWorkspaceData>["health"];
  loading: boolean;
  error: string | null;
  report: ExecutiveReportResponse | null;
  lastUpdated: string;
}) {
  const { t } = useTranslations("ui");
  const { scadaIsMock } = useOperasyon();
  const { getKpi, loading: aiLoading } = useAnnotations();
  const healthOk = health?.status === "ok";
  const riskLevel = severityFromRisk(data?.riskScore);
  const alertCount = data?.criticalAlertsCount ?? 0;
  const alertLevel: StatusLevel = alertCount > 0 ? "crit" : "normal";
  const costFmt = formatCurrencyCompact(data?.totalImbalanceCostTl ?? 0);
  const costLevel: StatusLevel = (data?.totalImbalanceCostTl ?? 0) > 100000 ? "warn" : "normal";
  const topRule = data?.rules?.[0]
    ? localizeRule(t, data.rules[0], scadaIsMock).message
    : t("home.noActiveCriticalRisk");
  const alertsAnnotation = getKpi("critical_alerts");
  const highestRiskBorder = resolveKpiBorderLevel(
    alertsAnnotation?.severity,
    data?.rules?.[0] ? "warn" : "neutral",
  );

  return (
    <div className="h-full min-h-0 overflow-y-auto p-2">
      <section className="mb-2 grid gap-2 md:grid-cols-3">
        <SummaryCard
          label={t("home.riskStatus")}
          value={`${loading ? "—" : (data?.riskScore ?? "—")}/100`}
          level={riskLevel}
          hint={topRule}
          annotation={getKpi("risk")}
          aiLoading={aiLoading}
        />
        <SummaryCard
          label={t("home.criticalAlarms")}
          value={loading ? "—" : String(alertCount)}
          level={alertLevel}
          hint={alertCount > 0 ? t("home.triageRequiredHint") : t("home.noAlarms")}
          annotation={alertsAnnotation}
          aiLoading={aiLoading}
        />
        <SummaryCard
          label={t("home.imbalanceCost")}
          value={loading ? "—" : `${costFmt.display} TL`}
          level={costLevel}
          hint={t("home.lastUpdateHint", { time: lastUpdated })}
          annotation={getKpi("imbalance_cost")}
          aiLoading={aiLoading}
        />
      </section>

      <section className="mb-2 grid grid-cols-2 gap-1 md:grid-cols-3 xl:grid-cols-6">
        <AnnotatedKpiCell
          kpiId="production"
          label={t("home.production")}
          value={loading ? "—" : (data?.hourlyProduction?.[data.hourlyProduction.length - 1]?.actual_mw ?? data?.forecastMw ?? 0).toFixed(1)}
          unit="MW"
          updatedAt={lastUpdated}
        />
        <AnnotatedKpiCell
          kpiId="forecast"
          label={t("forecast.forecast")}
          value={loading ? "—" : (data?.forecastMw ?? 0).toFixed(1)}
          unit="MW"
          sub={data?.targetDate}
        />
        <AnnotatedKpiCell
          kpiId="risk"
          label={t("forecast.risk")}
          value={loading ? "—" : String(data?.riskScore ?? "—")}
          unit="/100"
          status={riskLevel === "crit" || riskLevel === "warn" ? riskLevel : "neutral"}
        />
        <AnnotatedKpiCell
          kpiId="imbalance_cost"
          label={t("commonUi.cost")}
          value={loading ? "—" : ""}
          unit="TL"
          compactCurrency={data?.totalImbalanceCostTl}
          status={costLevel === "warn" ? "warn" : "neutral"}
        />
        <AnnotatedKpiCell
          kpiId="live_mape"
          label={t("forecast.liveMape")}
          value={loading ? "—" : formatMape(data?.liveMapePercentage)}
          unit="%"
          sub={data ? t("home.liveMapeMeta", { value: formatMape(data.averageMape) }) : undefined}
        />
        <AnnotatedKpiCell
          kpiId="critical_alerts"
          label={t("home.alerts")}
          value={loading ? "—" : String(alertCount)}
          status={alertCount > 0 ? "crit" : "neutral"}
        />
      </section>

      {error ? <ErrorBanner message={error} className="mb-2" /> : null}

      <section className="mb-2 grid gap-2 md:grid-cols-3">
        <OpsPanel
          title={t("home.highestRisk")}
          meta={t("home.ruleEngineMeta")}
          className={emphasisBorderClass(highestRiskBorder)}
        >
          {data?.rules[0] ? (
            <>
              <p className={cn("text-[11px]", STATUS_COLORS[highestRiskBorder].text)}>{topRule}</p>
              <AiInlineHint annotation={alertsAnnotation} loading={aiLoading} />
            </>
          ) : (
            <p className="text-[10px] text-zinc-400">{t("home.noActiveRiskWarning")}</p>
          )}
          <Link
            href={WORKSPACES[WORKSPACE_IDS.risk].href}
            className="mt-2 inline-block text-[10px] text-zinc-500 hover:text-zinc-300"
          >
            {t("home.riskDashboardLink")} →
          </Link>
        </OpsPanel>

        <Link
          href={WORKSPACES[WORKSPACE_IDS.monitoring].href}
          className={cn(
            "flex flex-col justify-between border border-[#27272A] border-l-2 bg-[#18181B] p-2 hover:bg-[#1C1C1F]",
            loading ? "border-l-zinc-600" : healthOk ? "border-l-emerald-500" : "border-l-rose-500",
          )}
        >
          <div>
            <p
              className={cn(
                "text-[10px] font-semibold uppercase",
                loading ? "text-zinc-400" : healthOk ? "text-emerald-400" : "text-rose-400",
              )}
            >
              {t("home.system")}
            </p>
            <p className="mt-1 text-[10px] text-zinc-600">{t("monitoring.apiStatus")}</p>
            <div
              className={cn(
                "mt-2 flex items-center gap-1.5 text-[11px]",
                loading ? "text-zinc-500" : healthOk ? "text-emerald-400" : "text-rose-400",
              )}
            >
              <span
                className={cn(
                  "h-1.5 w-1.5 shrink-0",
                  loading ? "bg-zinc-600" : healthOk ? "bg-emerald-500" : "bg-rose-500",
                )}
              />
              <span>{healthOk ? t("home.systemActive") : t("home.checkRequired")}</span>
            </div>
          </div>
          <span className="mt-2 inline-flex items-center text-[10px] text-zinc-300">
            {t("home.monitoringLink")} <ArrowRight className="ml-1 h-3 w-3" />
          </span>
        </Link>

        <Link
          href={APP_ROUTES.operations}
          className="flex flex-col justify-between border border-[#27272A] border-l-2 border-l-[#3B82F6] bg-[#18181B] p-2 hover:bg-[#1C1C1F]"
        >
          <div>
            <p className="text-[10px] font-semibold uppercase text-[#3B82F6]">{t("home.opsCenter")}</p>
            <p className="mt-1 text-[10px] text-zinc-600">{t("home.liveControlRoom")}</p>
          </div>
          <span className="mt-2 inline-flex items-center text-[10px] text-zinc-300">
            {t("commonUi.goTo")} <ArrowRight className="ml-1 h-3 w-3" />
          </span>
        </Link>
      </section>

      <section className="mb-2">
        <OpsPanel title={t("home.executiveSummary")} meta={t("home.lastReportMeta")}>
          {report ? (
            <>
              <p className="line-clamp-4 text-[10px] leading-relaxed text-zinc-400">{report.executive_summary}</p>
              <div className="mt-2 flex flex-wrap gap-3 font-mono text-[9px] text-zinc-600">
                <span>{t("home.liveMapeMeta", { value: formatMape(data?.liveMapePercentage) })}</span>
                <span>{formatCurrencyTl(report.total_imbalance_cost_tl)}</span>
              </div>
              <Link
                href={WORKSPACES[WORKSPACE_IDS.reports].href}
                className="mt-2 inline-block text-[10px] text-[#3B82F6] hover:underline"
              >
                {t("home.reportCenterLink")} →
              </Link>
            </>
          ) : (
            <p className="text-[10px] text-zinc-600">{t("home.reportLoading")}</p>
          )}
        </OpsPanel>
      </section>

      <OpsPanel title={t("home.pendingDecisions")} meta={t("risk.decisionCenter")}>
        <p className="text-[10px] text-zinc-500">{t("home.pendingDecisionsHint")}</p>
        <Link
          href={WORKSPACES[WORKSPACE_IDS.ai].href}
          className="mt-2 inline-block text-[10px] text-[#3B82F6] hover:underline"
        >
          {t("risk.decisionCenter")} →
        </Link>
      </OpsPanel>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  level,
  hint,
  annotation,
  aiLoading,
}: {
  label: string;
  value: string;
  level: StatusLevel;
  hint: string;
  annotation?: BriefingAnnotation;
  aiLoading?: boolean;
}) {
  const borderLevel = resolveKpiBorderLevel(annotation?.severity, levelToKpiStatus(level));
  const colors = STATUS_COLORS[borderLevel];
  return (
    <div className={cn(emphasisBorderClass(borderLevel), "p-3")}>
      <p className="text-[9px] font-semibold uppercase tracking-[0.08em] text-zinc-500">{label}</p>
      <p className={cn("mt-1 font-mono text-xl font-medium tabular-nums", colors.text)}>{value}</p>
      <p className="mt-1 line-clamp-2 text-[10px] text-zinc-600">{hint}</p>
      <AiInlineHint annotation={annotation} loading={aiLoading} compact />
    </div>
  );
}
