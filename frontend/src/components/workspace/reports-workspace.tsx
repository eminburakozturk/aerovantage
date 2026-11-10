"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, Download, FileJson, FileSpreadsheet, FileText } from "lucide-react";
import { useSearchParams } from "next/navigation";

import { KpiCell } from "@/components/ops/kpi-cell";
import { OpsPanel } from "@/components/ops/ops-panel";
import { ErrorBanner } from "@/components/ui/async-state";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useOperasyon } from "@/context/operasyon-context";
import { useLocale, useTranslations } from "@/context/locale-context";
import {
  askAboutReport,
  downloadExecutiveCsv,
  downloadExecutiveExcel,
  downloadExecutivePdf,
  downloadHistoryCsv,
  fetchExecutiveReport,
  fetchPortfolioReport,
  fetchWeeklyReport,
  runScenario,
  type ExecutiveReportResponse,
  type PipelineHistoryEntry,
  type PortfolioReportResponse,
  type ScenarioResult,
  type WeeklyReportResponse,
} from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  REPORT_TYPES,
  type ReportType,
  filterScorecardsForType,
  normalizeReportType,
  readLastWorkspace,
  rememberReportType,
  resolveInitialReportType,
  sectionVisible,
} from "@/lib/report-types";
import { levelToKpiStatus, normalizeSeverity } from "@/lib/status-level";
import { useUserMessages } from "@/lib/user-messages";
import { cn } from "@/lib/utils";

interface ReportsWorkspaceProps {
  tab: string;
  history: PipelineHistoryEntry[];
}

export function ReportsWorkspace({ tab, history }: ReportsWorkspaceProps) {
  const { assets, selectedAssetId, pipelineEpoch } = useOperasyon();
  const { locale } = useLocale();
  const { t } = useTranslations("ui");
  const { getErrorMessage } = useUserMessages();
  const searchParams = useSearchParams();
  const [reportType, setReportType] = useState<ReportType>("executive");
  const [typeReady, setTypeReady] = useState(false);
  const [executive, setExecutive] = useState<ExecutiveReportResponse | null>(null);
  const [portfolio, setPortfolio] = useState<PortfolioReportResponse | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const loadedForAsset = useRef<string | null>(null);
  const typeInitRef = useRef(false);
  const fetchGen = useRef(0);

  const portfolioIds = useMemo(() => assets.map((a) => a.id), [assets]);
  const portfolioKey = portfolioIds.join(",");

  // Initialize report type once (URL > storage > workspace). Do not re-reset on tab changes.
  useEffect(() => {
    if (typeInitRef.current) return;
    typeInitRef.current = true;
    const initial = resolveInitialReportType({
      urlType: searchParams.get("type"),
      workspace: readLastWorkspace(),
    });
    setReportType(initial);
    setTypeReady(true);
  }, [searchParams]);

  const onReportTypeChange = (next: ReportType) => {
    setReportType(next);
    rememberReportType(next);
    // Drop stale pack so section filter uses client map until new fetch lands
    setExecutive((prev) =>
      prev && prev.report_type === next ? prev : prev ? { ...prev, report_type: next, visible_sections: [] } : prev,
    );
  };

  const load = useCallback(
    async (silent = false) => {
      if (!selectedAssetId || !typeReady) return;
      const gen = ++fetchGen.current;
      if (!silent) setRefreshing(true);
      setError(null);
      try {
        const exec = await fetchExecutiveReport(
          selectedAssetId,
          30,
          locale,
          reportType,
          readLastWorkspace(),
        );
        if (gen !== fetchGen.current) return;
        setExecutive(exec);
        if (portfolioIds.length >= 2) {
          const port = await fetchPortfolioReport(portfolioIds, 30, locale);
          if (gen !== fetchGen.current) return;
          setPortfolio(port);
        } else {
          setPortfolio(null);
        }
        loadedForAsset.current = `${selectedAssetId}:${reportType}:${locale}`;
      } catch (err) {
        if (gen !== fetchGen.current) return;
        setError(getErrorMessage(err, t("reports.loadFailed")));
      } finally {
        if (gen === fetchGen.current) {
          setInitialLoading(false);
          setRefreshing(false);
        }
      }
    },
    [selectedAssetId, portfolioIds, getErrorMessage, t, locale, reportType, typeReady],
  );

  useEffect(() => {
    if (!selectedAssetId || !typeReady) return;
    const key = `${selectedAssetId}:${reportType}:${locale}`;
    const silent = loadedForAsset.current === key;
    void load(silent);
  }, [selectedAssetId, portfolioKey, load, locale, reportType, typeReady, pipelineEpoch]);

  const showKpiLoading = initialLoading && !executive;

  if (error && !executive) {
    return <ErrorBanner message={error} />;
  }

  switch (tab) {
    case "daily":
      return <DailyTab history={history} loading={initialLoading} />;
    case "weekly":
      return <WeeklyTab assetId={selectedAssetId} loading={initialLoading} />;
    case "portfolio":
      return <PortfolioTab portfolio={portfolio} loading={showKpiLoading} />;
    case "export":
      return (
        <ExportTab
          assetId={selectedAssetId}
          executive={executive}
          portfolio={portfolio}
          history={history}
          loading={showKpiLoading}
          locale={locale}
          reportType={reportType}
        />
      );
    default:
      return (
        <ExecutiveTab
          executive={executive}
          loading={showKpiLoading}
          refreshing={refreshing}
          error={error}
          onRefresh={() => void load(false)}
          reportType={reportType}
          onReportTypeChange={onReportTypeChange}
          assetId={selectedAssetId}
          locale={locale}
        />
      );
  }
}

function ExecutiveTab({
  executive,
  loading,
  refreshing,
  error,
  onRefresh,
  reportType,
  onReportTypeChange,
  assetId,
  locale,
}: {
  executive: ExecutiveReportResponse | null;
  loading: boolean;
  refreshing?: boolean;
  error?: string | null;
  onRefresh: () => void;
  reportType: ReportType;
  onReportTypeChange: (type: ReportType) => void;
  assetId: string;
  locale: string;
}) {
  const { t, bcp47 } = useTranslations("ui");
  const { getErrorMessage } = useUserMessages();
  const [downloading, setDownloading] = useState<"pdf" | "excel" | "csv" | "history-csv" | "json" | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const show = (section: string) =>
    sectionVisible(reportType, section, executive?.visible_sections, executive?.report_type);
  const reportTitle = t(`reports.type.${reportType}`);
  const cards = filterScorecardsForType(reportType, executive?.scorecards ?? []);
  const brief = executive?.ai_brief;
  const financial = executive?.financial ?? {};
  const forecast = executive?.forecast ?? {};
  const operational = executive?.operational ?? {};
  const risk = executive?.risk ?? {};
  const dataIntel = executive?.data_intelligence ?? {};
  const modelIntel = executive?.model_intelligence ?? {};
  const recommendations = executive?.recommendations ?? [];
  const actions = executive?.actions ?? [];
  const trends = executive?.trends;
  const benchmark = executive?.benchmark ?? {};
  const changes = executive?.changes_since_last ?? {};

  const fmtNum = (v: unknown, digits = 1) => {
    const n = typeof v === "number" ? v : Number(v);
    if (!Number.isFinite(n)) return "—";
    return n.toLocaleString(bcp47, { maximumFractionDigits: digits });
  };

  const downloadJsonPack = () => {
    if (!executive) return;
    const blob = new Blob([JSON.stringify(executive, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${reportType}-${executive.asset_id ?? assetId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const runDownload = async (format: "pdf" | "excel" | "csv" | "history-csv" | "json") => {
    if (!assetId) return;
    setDownloading(format);
    setDownloadError(null);
    try {
      if (format === "pdf") await downloadExecutivePdf(assetId, 30, locale, reportType);
      else if (format === "excel") await downloadExecutiveExcel(assetId, 30, locale, reportType);
      else if (format === "csv") await downloadExecutiveCsv(assetId, 30, locale, reportType);
      else if (format === "history-csv") await downloadHistoryCsv(assetId, 30, locale);
      else downloadJsonPack();
    } catch (err) {
      setDownloadError(getErrorMessage(err, t("reports.exportFailed")));
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="space-y-2">
      {error ? <ErrorBanner message={error} className="mb-2" /> : null}
      {downloadError ? <ErrorBanner message={downloadError} className="mb-2" /> : null}

      <div className="flex items-center justify-between gap-3 border border-[#27272A] bg-[#18181B] px-3 py-2">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <FileText className="h-4 w-4 shrink-0 text-[#3B82F6]" />
          <div className="min-w-0">
            <p className="truncate text-[11px] font-medium leading-tight text-zinc-200">{reportTitle}</p>
            <p className="truncate text-[9px] leading-tight text-zinc-600">
              {t("reports.executiveMetaBase", { asset: executive?.asset_id ?? "—", days: executive?.period_days ?? 30 })}
              {refreshing ? t("reports.updatingSuffix") : ""}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <div className="inline-flex h-8 items-center gap-2">
            <label
              className="whitespace-nowrap text-[9px] uppercase leading-none tracking-wide text-zinc-600"
              htmlFor="report-type-select"
            >
              {t("reports.reportType")}
            </label>
            <select
              id="report-type-select"
              value={reportType}
              onChange={(e) => onReportTypeChange(normalizeReportType(e.target.value))}
              className="h-8 max-w-[200px] appearance-none border border-[#3B82F6]/50 bg-[#0c0c0e] bg-[length:10px_6px] bg-[right_8px_center] bg-no-repeat py-0 pl-2 pr-7 text-[10px] leading-none text-zinc-100"
              style={{
                backgroundImage:
                  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath fill='%23a1a1aa' d='M0 0l5 6 5-6z'/%3E%3C/svg%3E\")",
              }}
            >
              {REPORT_TYPES.map((type) => (
                <option key={type} value={type}>
                  {t(`reports.type.${type}`)}
                </option>
              ))}
            </select>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onRefresh}
            disabled={refreshing}
            className="h-8 rounded-none px-2 text-[10px] text-zinc-400 hover:bg-[#0c0c0e] hover:text-zinc-200"
          >
            {t("reports.refresh")}
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                disabled={!assetId || downloading !== null}
                className="h-8 rounded-none gap-1 px-2 text-[10px] text-zinc-400 hover:bg-[#0c0c0e] hover:text-zinc-200"
              >
                <Download className="h-3 w-3" />
                {t("reports.download")}
                <ChevronDown className="h-3 w-3 opacity-60" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="min-w-[10.5rem] rounded-none border-[#27272A] bg-[#18181B] p-1 text-zinc-200">
              <DropdownMenuItem
                className="rounded-none text-[11px] focus:bg-[#0c0c0e]"
                disabled={downloading !== null}
                onSelect={() => void runDownload("pdf")}
              >
                <FileText className="h-3.5 w-3.5 text-[#3B82F6]" />
                {t("reports.downloadPdf")}
              </DropdownMenuItem>
              <DropdownMenuItem
                className="rounded-none text-[11px] focus:bg-[#0c0c0e]"
                disabled={downloading !== null}
                onSelect={() => void runDownload("excel")}
              >
                <FileSpreadsheet className="h-3.5 w-3.5 text-[#3B82F6]" />
                {t("reports.downloadExcel")}
              </DropdownMenuItem>
              <DropdownMenuItem
                className="rounded-none text-[11px] focus:bg-[#0c0c0e]"
                disabled={downloading !== null}
                onSelect={() => void runDownload("csv")}
              >
                <FileText className="h-3.5 w-3.5 text-[#3B82F6]" />
                {t("reports.downloadCsv")}
              </DropdownMenuItem>
              <DropdownMenuSeparator className="bg-[#27272A]" />
              <DropdownMenuItem
                className="rounded-none text-[11px] focus:bg-[#0c0c0e]"
                disabled={downloading !== null}
                onSelect={() => void runDownload("history-csv")}
              >
                <FileText className="h-3.5 w-3.5 text-zinc-500" />
                {t("reports.downloadHistoryCsv")}
              </DropdownMenuItem>
              <DropdownMenuItem
                className="rounded-none text-[11px] focus:bg-[#0c0c0e]"
                disabled={downloading !== null || !executive}
                onSelect={() => void runDownload("json")}
              >
                <FileJson className="h-3.5 w-3.5 text-zinc-500" />
                {t("reports.downloadJson")}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {executive?.adaptive_hint && reportType === "executive" ? (
        <p className="border border-[#27272A] bg-[#0c0c0e] px-3 py-1.5 text-[10px] text-zinc-500">{executive.adaptive_hint}</p>
      ) : null}

      {refreshing ? (
        <p className="px-1 text-[10px] text-zinc-500">{t("reports.switchingType", { type: reportTitle })}</p>
      ) : null}

      {show("summary") ? (
        <OpsPanel title={t("home.executiveSummary")} meta={executive?.generated_at ? formatDateTime(executive.generated_at) : undefined}>
          <p className="text-[12px] leading-relaxed text-zinc-300">{executive?.executive_summary ?? "—"}</p>
        </OpsPanel>
      ) : null}

      {show("changes") ? (
        <OpsPanel title={t("reports.whatChanged")}>
          <p className="text-[11px] leading-relaxed text-zinc-300">{String(changes.summary ?? "—")}</p>
          <div className="mt-2 grid gap-2 sm:grid-cols-3 text-[10px]">
            <MetaRow label={t("reports.costDelta")} value={`${fmtNum(changes.cost_delta_pct)}%`} />
            <MetaRow label={t("reports.mapeDelta")} value={fmtNum(changes.mape_delta)} />
            <MetaRow label={t("reports.riskDelta")} value={fmtNum(changes.risk_delta)} />
          </div>
        </OpsPanel>
      ) : null}

      {show("ai_brief") ? (
        <OpsPanel title={brief?.title || t("reports.aiBrief")} meta={brief?.simulation ? t("reports.simNote") : undefined}>
          {loading && !brief ? (
            <div className="min-h-[88px] text-[11px] text-zinc-600">{t("reports.reportLoading")}</div>
          ) : (
            <div className="min-h-[88px] space-y-2 text-[11px] text-zinc-300">
              {brief?.focus ? <p className="text-[10px] text-[#00B8FF]/90">{brief.focus}</p> : null}
              <p className="leading-relaxed">{brief?.status_summary ?? "—"}</p>
              <div className="grid gap-2 sm:grid-cols-2">
                <MetaRow label={t("reports.topEvent")} value={String(brief?.top_event ?? "—")} />
                <MetaRow label={t("reports.topRisk")} value={String(brief?.top_risk ?? "—")} />
                <MetaRow label={t("commonUi.cost")} value={String(brief?.financial_impact ?? "—")} />
                <MetaRow label={t("reports.recommendedAction")} value={String(brief?.recommended_action ?? "—")} />
                <MetaRow label={t("reports.confidence")} value={brief?.confidence != null ? String(brief.confidence) : "—"} />
              </div>
            </div>
          )}
        </OpsPanel>
      ) : null}

      {show("scorecards") ? (
        <OpsPanel title={t("reports.scorecards")}>
          <section className="grid grid-cols-2 border border-[#27272A] bg-[#0c0c0e] sm:grid-cols-4 [&>*]:min-w-0 [&>*]:border-r [&>*]:border-[#27272A] [&>*:nth-child(2n)]:border-r-0 sm:[&>*:nth-child(2n)]:border-r sm:[&>*:nth-child(4n)]:border-r-0">
            {(loading && cards.length === 0
              ? [
                  { id: "1", label: t("commonUi.cost"), value: "—", level: "ok" },
                  { id: "2", label: t("forecast.mape"), value: "—", level: "ok" },
                  { id: "3", label: t("reports.critical"), value: "—", level: "ok" },
                  { id: "4", label: t("forecast.risk"), value: "—", level: "ok" },
                ]
              : cards
            ).map((card) => {
              const level = normalizeSeverity(card.level);
              const status = levelToKpiStatus(level);
              const accent =
                level === "warn"
                  ? "border-l-2 border-l-amber-500"
                  : level === "crit"
                    ? "border-l-2 border-l-rose-500"
                    : "";
              return (
                <div key={card.id} className={cn("overflow-hidden", accent)}>
                  <KpiCell
                    label={card.label}
                    value={loading ? "—" : card.value}
                    sub={
                      card.note
                      || (card.level_label && card.level_label !== card.value
                        ? card.level_label
                        : undefined)
                    }
                    status={status}
                    compact
                    className="border-r-0"
                  />
                </div>
              );
            })}
          </section>
        </OpsPanel>
      ) : null}

      <div className="grid gap-2 lg:grid-cols-2">
        {show("financial") ? (
          <OpsPanel title={t("reports.financialIntel")}>
            <div className="space-y-1.5 text-[11px]">
              <MetaRow label={t("reports.totalCost")} value={`${fmtNum(financial.total_cost_tl, 0)} TL`} />
              <MetaRow label={t("reports.avgDailyCost")} value={`${fmtNum(financial.average_daily_cost_tl, 0)} TL`} />
              <MetaRow
                label={t("reports.costTrend")}
                value={
                  String(
                    financial.cost_trend_label
                      ?? (financial.cost_trend === "up"
                        ? t("reports.trendUp")
                        : financial.cost_trend === "down"
                          ? t("reports.trendDown")
                          : financial.cost_trend === "flat"
                            ? t("reports.trendFlat")
                            : financial.cost_trend
                              ?? "—"),
                  )
                }
              />
              <MetaRow label={t("reports.avoidableCost")} value={`${fmtNum(financial.avoidable_cost_estimate_tl, 0)} TL`} />
              <MetaRow label={t("reports.revenueRisk")} value={`${fmtNum(financial.revenue_risk_tl, 0)} TL`} />
            </div>
          </OpsPanel>
        ) : null}
        {show("forecast") ? (
          <OpsPanel title={t("reports.forecastIntel")}>
            <div className="space-y-1.5 text-[11px]">
              <MetaRow label={t("reports.avgMape")} value={`%${fmtNum(forecast.average_mape)}`} />
              <MetaRow label={t("reports.rmse")} value={String(forecast.rmse ?? "—")} />
              <MetaRow label={t("reports.mae")} value={String(forecast.mae ?? "—")} />
              <MetaRow label={t("reports.confidence")} value={String(forecast.confidence ?? "—")} />
            </div>
          </OpsPanel>
        ) : null}
        {show("operational") ? (
          <OpsPanel title={t("reports.operationalIntel")}>
            <div className="space-y-1.5 text-[11px]">
              <MetaRow label={t("reports.critical")} value={String(operational.critical_count ?? 0)} />
              <MetaRow label={t("reports.warnings")} value={String(operational.warning_count ?? 0)} />
              <MetaRow label={t("reports.activeRules")} value={String(operational.active_rules ?? 0)} />
              <MetaRow label={t("forecast.records")} value={String(operational.pipeline_runs ?? 0)} />
            </div>
          </OpsPanel>
        ) : null}
        {show("risk") ? (
          <OpsPanel title={t("reports.riskIntel")}>
            <div className="space-y-1.5 text-[11px]">
              <MetaRow label={t("forecast.risk")} value={String(risk.average_score ?? "—")} />
              <MetaRow label={t("reports.status")} value={String(risk.level_label ?? risk.level ?? "—")} />
              <MetaRow label={t("reports.topRisk")} value={String(risk.top_rule ?? "—")} />
              <MetaRow label={t("reports.revenueRisk")} value={`${fmtNum(risk.financial_risk_tl, 0)} TL`} />
            </div>
          </OpsPanel>
        ) : null}
        {show("data") ? (
          <OpsPanel title={t("reports.dataIntel")}>
            <div className="space-y-1.5 text-[11px]">
              <MetaRow label={t("reports.trustScore")} value={String(dataIntel.trust_score ?? dataIntel.average_score ?? "—")} />
              <MetaRow label={t("reports.gate")} value={String(dataIntel.gate_passed ?? "—")} />
            </div>
          </OpsPanel>
        ) : null}
        {show("model") ? (
          <OpsPanel title={t("reports.modelIntel")}>
            <div className="space-y-1.5 text-[11px]">
              <MetaRow label={t("reports.confidence")} value={String(modelIntel.confidence ?? "—")} />
              <MetaRow label={t("reports.drift")} value={String(modelIntel.drift_detected ?? "—")} />
              <MetaRow label={t("reports.modelVersion")} value={String(modelIntel.model_version ?? "—")} />
              <MetaRow label={t("reports.physicsFallback")} value={String(modelIntel.physics_fallback ?? "—")} />
            </div>
          </OpsPanel>
        ) : null}
      </div>

      {show("recommendations") ? (
        <OpsPanel title={t("reports.recommendations")}>
          <ul className="space-y-1.5">
            {(recommendations.length ? recommendations : [{ title: "—" }]).slice(0, 8).map((rec, i) => (
              <li key={i} className="border border-[#27272A] px-2 py-1.5 text-[11px] text-zinc-300">
                <span className="text-zinc-500">
                  {rec.priority_label || rec.priority
                    ? `[${rec.priority_label ?? (rec.priority === "high" ? t("reports.priorityHigh") : rec.priority === "low" ? t("reports.priorityLow") : t("reports.priorityMedium"))}] `
                    : ""}
                </span>
                {rec.title}
              </li>
            ))}
          </ul>
        </OpsPanel>
      ) : null}

      {show("actions") ? (
        <OpsPanel title={t("reports.actionCenter")}>
          <table className="w-full text-[10px]">
            <thead>
              <tr className="border-b border-[#27272A] text-left text-zinc-600">
                <th className="pb-2 pr-2">ID</th>
                <th className="pb-2 pr-2">{t("reports.recommendedAction")}</th>
                <th className="pb-2 pr-2">{t("reports.priority")}</th>
                <th className="pb-2 pr-2">{t("reports.status")}</th>
                <th className="pb-2">{t("reports.owner")}</th>
              </tr>
            </thead>
            <tbody>
              {(actions.length ? actions : [{ id: "—", title: "—", priority_label: "—", status: "—", owner: "—" }]).map((a, i) => (
                <tr key={a.id ?? i} className="border-b border-[#27272A]/50 text-zinc-400">
                  <td className="py-1.5 pr-2 font-mono">{a.id ?? "—"}</td>
                  <td className="py-1.5 pr-2 text-zinc-300">{a.title ?? "—"}</td>
                  <td className="py-1.5 pr-2">{a.priority_label ?? a.priority ?? "—"}</td>
                  <td className="py-1.5 pr-2">{a.status ?? "—"}</td>
                  <td className="py-1.5">{a.owner ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </OpsPanel>
      ) : null}

      <div className="grid gap-2 lg:grid-cols-2">
        {show("trends") ? (
          <OpsPanel title={t("reports.trendAnalysis")}>
            <div className="space-y-2 text-[11px] text-zinc-400">
              <SparkRow label={t("commonUi.cost")} values={trends?.cost_sparkline} />
              <SparkRow label={t("forecast.mape")} values={trends?.mape_sparkline} />
              <SparkRow label={t("forecast.risk")} values={trends?.risk_sparkline} />
            </div>
          </OpsPanel>
        ) : null}
        {show("benchmark") ? (
          <OpsPanel title={t("reports.benchmark")}>
            <div className="space-y-1.5 text-[11px]">
              <MetaRow label={t("reports.vsPrior")} value={`${fmtNum(benchmark.vs_prior_cost_pct)}%`} />
              <MetaRow label={t("reports.portfolioMape")} value={benchmark.portfolio_avg_mape != null ? `%${fmtNum(benchmark.portfolio_avg_mape)}` : "—"} />
              <MetaRow label={t("reports.avgDailyCost")} value={`${fmtNum(benchmark.recent_period_avg_cost_tl, 0)} TL`} />
            </div>
          </OpsPanel>
        ) : null}
      </div>

      {show("whatif") ? <ReportWhatIf assetId={assetId} locale={locale} /> : null}
      {show("chat") ? <ReportChat assetId={assetId} locale={locale} reportType={reportType} /> : null}

      {show("conclusion") ? (
        <OpsPanel title={t("reports.conclusion")}>
          <p className="text-[12px] leading-relaxed text-zinc-300">{executive?.conclusion || executive?.executive_summary || "—"}</p>
        </OpsPanel>
      ) : null}
    </div>
  );
}

function ReportChat({
  assetId,
  locale,
  reportType,
}: {
  assetId: string;
  locale: string;
  reportType: ReportType;
}) {
  const { t } = useTranslations("ui");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);
  const [asked, setAsked] = useState(false);
  const answerRef = useRef<HTMLDivElement | null>(null);

  const ask = async () => {
    if (!assetId || !question.trim()) return;
    setAsking(true);
    setAsked(true);
    setAnswer(null);
    try {
      const res = await askAboutReport(assetId, question.trim(), locale, reportType);
      const text = typeof res?.answer === "string" ? res.answer.trim() : "";
      if (!text) {
        setAnswer(t("reports.askFailed"));
      } else {
        setAnswer(text);
        requestAnimationFrame(() => {
          answerRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
        });
      }
    } catch {
      setAnswer(t("reports.askFailed"));
    } finally {
      setAsking(false);
    }
  };

  return (
    <OpsPanel title={t("reports.askAboutReport")}>
      <div className="flex gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={t("reports.askPlaceholder")}
          className="h-8 flex-1 border border-[#27272A] bg-[#0c0c0e] px-2 text-[11px] text-zinc-200"
          onKeyDown={(e) => {
            if (e.key === "Enter") void ask();
          }}
        />
        <Button type="button" size="sm" className="h-8 rounded-none text-[10px]" disabled={asking || !question.trim()} onClick={() => void ask()}>
          {asking ? "…" : t("reports.ask")}
        </Button>
      </div>
      {asked ? (
        <div
          ref={answerRef}
          className="mt-2 min-h-[56px] border border-[#27272A] bg-[#0c0c0e] px-2 py-2 text-[11px] leading-relaxed text-zinc-300"
        >
          {asking ? <p className="text-zinc-500">{t("reports.askLoading")}</p> : null}
          {!asking && answer ? <p className="whitespace-pre-wrap">{answer}</p> : null}
        </div>
      ) : null}
    </OpsPanel>
  );
}

function ReportWhatIf({ assetId, locale }: { assetId: string; locale: string }) {
  const { t, bcp47 } = useTranslations("ui");
  const [windAdj, setWindAdj] = useState(-10);
  const [ptfAdj, setPtfAdj] = useState(15);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<ScenarioResult | null>(null);

  const run = async () => {
    if (!assetId) return;
    setRunning(true);
    try {
      setResult(
        await runScenario(
          {
            asset_id: assetId,
            wind_adjustment_pct: windAdj,
            ptf_adjustment_pct: ptfAdj,
            turbines_down: 0,
          },
          locale,
        ),
      );
    } catch {
      setResult(null);
    } finally {
      setRunning(false);
    }
  };

  return (
    <OpsPanel title={t("reports.whatIf")} meta={t("reports.whatIfMeta")}>
      <div className="grid gap-2 sm:grid-cols-3">
        <label className="text-[10px] text-zinc-500">
          {t("scenarios.windChange")}
          <input
            type="number"
            value={windAdj}
            onChange={(e) => setWindAdj(Number(e.target.value))}
            className="mt-1 h-7 w-full border border-[#27272A] bg-[#0c0c0e] px-2 font-mono text-[11px] text-zinc-200"
          />
        </label>
        <label className="text-[10px] text-zinc-500">
          {t("scenarios.ptfChange")}
          <input
            type="number"
            value={ptfAdj}
            onChange={(e) => setPtfAdj(Number(e.target.value))}
            className="mt-1 h-7 w-full border border-[#27272A] bg-[#0c0c0e] px-2 font-mono text-[11px] text-zinc-200"
          />
        </label>
        <div className="flex items-end">
          <Button type="button" size="sm" className="h-7 w-full rounded-none text-[10px]" disabled={running || !assetId} onClick={() => void run()}>
            {running ? t("scenarios.running") : t("scenarios.runScenario")}
          </Button>
        </div>
      </div>
      {result ? (
        <p className="mt-2 text-[11px] leading-relaxed text-zinc-300">
          {result.summary}
          {` · ${result.adjusted_cost_tl.toLocaleString(bcp47)} TL`}
        </p>
      ) : null}
    </OpsPanel>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-[#27272A]/60 py-1.5">
      <span className="shrink-0 text-[10px] leading-snug text-zinc-500">{label}</span>
      <span className="min-w-0 flex-1 break-words text-right text-[11px] leading-snug text-zinc-300">{value}</span>
    </div>
  );
}

function SparkRow({ label, values }: { label: string; values?: number[] }) {
  const nums = (values ?? []).filter((n) => Number.isFinite(n));
  if (!nums.length) {
    return (
      <div className="flex justify-between gap-2">
        <span className="text-zinc-600">{label}</span>
        <span>—</span>
      </div>
    );
  }
  const lo = Math.min(...nums);
  const hi = Math.max(...nums);
  const span = hi - lo || 1;
  const bars = "▁▂▃▄▅▆▇█";
  const spark = nums
    .slice(-24)
    .map((n) => bars[Math.min(7, Math.floor(((n - lo) / span) * 7))])
    .join("");
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-zinc-600">{label}</span>
      <span className="font-mono tracking-tight text-zinc-300">{spark}</span>
    </div>
  );
}

function DailyTab({ history, loading }: { history: PipelineHistoryEntry[]; loading: boolean }) {
  const { t } = useTranslations("ui");
  return (
    <OpsPanel title={t("reports.dailyOpsReportTitle")} meta={t("reports.fromPipelineRecordsMeta")}>
      <table className="w-full text-[10px]">
        <thead>
          <tr className="border-b border-[#27272A] text-left text-zinc-600">
            <th className="pb-2 pr-3">{t("forecast.date")}</th>
            <th className="pb-2 pr-3">{t("risk.plant")}</th>
            <th className="pb-2 pr-3">{t("forecast.risk")}</th>
            <th className="pb-2 pr-3">{t("forecast.mape")}</th>
            <th className="pb-2">{t("reports.summary")}</th>
          </tr>
        </thead>
        <tbody>
          {history.slice(0, 15).map((entry, i) => (
            <tr key={i} className="border-b border-[#27272A]/50">
              <td className="py-2 pr-3 font-mono text-zinc-500">{entry.target_date}</td>
              <td className="py-2 pr-3 text-zinc-400">{entry.asset_name ?? entry.asset_id}</td>
              <td className="py-2 pr-3 font-mono text-zinc-400">{entry.risk_score ?? "—"}</td>
              <td className="py-2 pr-3 font-mono text-zinc-400">%{entry.mape_percentage?.toFixed(1) ?? "—"}</td>
              <td className="py-2 text-zinc-500">{entry.ai_insight?.slice(0, 80) ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {!loading && history.length === 0 ? <p className="py-4 text-[10px] text-zinc-600">{t("reports.noDailyRecords")}</p> : null}
    </OpsPanel>
  );
}

function WeeklyTab({ assetId, loading }: { assetId: string; loading: boolean }) {
  const { t, bcp47, locale } = useTranslations("ui");
  const [weekly, setWeekly] = useState<WeeklyReportResponse | null>(null);

  useEffect(() => {
    if (!assetId) return;
    void fetchWeeklyReport(assetId, 4, locale).then(setWeekly).catch(() => setWeekly(null));
  }, [assetId, locale]);

  return (
    <div className="space-y-2">
      <OpsPanel title={t("reports.weeklyReport")} meta={weekly?.summary}>
        <table className="w-full text-[10px]">
          <thead>
            <tr className="border-b border-[#27272A] text-left text-zinc-600">
              <th className="pb-2 pr-3">{t("reports.week")}</th>
              <th className="pb-2 pr-3">{t("forecast.records")}</th>
              <th className="pb-2 pr-3">{t("commonUi.cost")}</th>
              <th className="pb-2 pr-3">{t("forecast.mape")}</th>
              <th className="pb-2">{t("reports.maxRisk")}</th>
            </tr>
          </thead>
          <tbody>
            {weekly?.weeks.map((w) => (
              <tr key={w.week} className="border-b border-[#27272A]/50">
                <td className="py-2 pr-3 font-mono text-zinc-400">{w.week}</td>
                <td className="py-2 pr-3">{w.runs}</td>
                <td className="py-2 pr-3 font-mono">{w.total_cost_tl.toLocaleString(bcp47)} TL</td>
                <td className="py-2 pr-3 font-mono">%{w.average_mape.toFixed(1)}</td>
                <td className="py-2 font-mono">{w.max_risk_score}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && !weekly?.weeks.length ? <p className="py-4 text-[10px] text-zinc-600">{t("reports.noWeeklyData")}</p> : null}
      </OpsPanel>
    </div>
  );
}

function PortfolioTab({ portfolio, loading }: { portfolio: PortfolioReportResponse | null; loading: boolean }) {
  const { t, bcp47 } = useTranslations("ui");

  if (!portfolio && !loading) {
    return (
      <OpsPanel title={t("reports.portfolioReport")} meta={t("reports.multiAssetRequiredMeta")}>
        <p className="text-[11px] text-zinc-500">{t("reports.portfolioMinAssets")}</p>
      </OpsPanel>
    );
  }

  return (
    <div className="space-y-2">
      <section className="grid grid-cols-3 border border-[#27272A] bg-[#18181B]">
        <KpiCell
          label={t("risk.totalCost")}
          value={loading ? "—" : (portfolio?.total_cost?.toLocaleString(bcp47) ?? "—")}
          unit="TL"
        />
        <KpiCell label={t("forecast.avgMape")} value={loading ? "—" : (portfolio?.avg_mape.toFixed(1) ?? "—")} unit="%" />
        <KpiCell label={t("risk.plant")} value={loading ? "—" : String(portfolio?.asset_ids.length ?? 0)} />
      </section>

      <OpsPanel title={t("reports.portfolioSummary")} meta={portfolio?.asset_ids.join(", ")}>
        <p className="text-[11px] text-zinc-300">{portfolio?.summary ?? "—"}</p>
      </OpsPanel>

      {portfolio?.assets.length ? (
        <OpsPanel title={t("reports.assetDetail")} meta={t("reports.individualReportsMeta")}>
          <div className="space-y-2">
            {portfolio.assets.map((asset) => (
              <div key={asset.asset_id} className="border border-[#27272A] p-2">
                <p className="text-[10px] font-medium text-zinc-300">{asset.asset_id}</p>
                <p className="mt-1 text-[10px] text-zinc-500">{asset.executive_summary.slice(0, 120)}...</p>
              </div>
            ))}
          </div>
        </OpsPanel>
      ) : null}
    </div>
  );
}

function ExportTab({
  assetId,
  executive,
  portfolio,
  history,
  loading,
  locale,
  reportType,
}: {
  assetId: string;
  executive: ExecutiveReportResponse | null;
  portfolio: PortfolioReportResponse | null;
  history: PipelineHistoryEntry[];
  loading: boolean;
  locale: string;
  reportType: ReportType;
}) {
  const { t } = useTranslations("ui");
  const { getErrorMessage } = useUserMessages();
  const [exporting, setExporting] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  const downloadJson = (filename: string, data: unknown) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const runExport = async (id: string, fn: () => Promise<void>) => {
    setExporting(id);
    setExportError(null);
    try {
      await fn();
    } catch (err) {
      setExportError(getErrorMessage(err, t("reports.exportFailed")));
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="space-y-2">
      <p className="text-[11px] text-zinc-500">{t("reports.exportIntro")}</p>

      {exportError ? (
        <ErrorBanner message={exportError} className="mb-2" />
      ) : null}

      <div className="grid gap-2 sm:grid-cols-2">
        <ExportCard
          title={`${t("reports.executiveReport")} (PDF)`}
          description={t("reports.executivePdfDesc")}
          disabled={loading || !assetId || exporting !== null}
          onClick={() => void runExport("pdf", () => downloadExecutivePdf(assetId, 30, locale, reportType))}
        />
        <ExportCard
          title={`${t("reports.reportPackage")} (Excel)`}
          description={t("reports.reportPackageDesc")}
          disabled={loading || !assetId || exporting !== null}
          onClick={() => void runExport("excel", () => downloadExecutiveExcel(assetId, 30, locale, reportType))}
        />
        <ExportCard
          title={`${t("reports.pipelineHistory")} (CSV)`}
          description={t("reports.backendCsvExportDesc")}
          disabled={loading || !assetId || exporting !== null}
          onClick={() => void runExport("csv", () => downloadHistoryCsv(assetId, 30, locale))}
        />
        <ExportCard
          title={`${t("reports.executiveReport")} (JSON)`}
          description={t("reports.executiveJsonDesc")}
          disabled={loading || !executive}
          onClick={() => downloadJson(`executive-${executive?.asset_id}.json`, executive)}
        />
        <ExportCard
          title={`${t("reports.portfolioReport")} (JSON)`}
          description={t("reports.portfolioJsonDesc")}
          disabled={loading || !portfolio}
          onClick={() => downloadJson("portfolio-report.json", portfolio)}
        />
        <ExportCard
          title={`${t("reports.pipelineHistory")} (JSON)`}
          description={t("reports.fullRecordDataDesc")}
          disabled={loading || history.length === 0}
          onClick={() => downloadJson("pipeline-history.json", history)}
        />
      </div>
    </div>
  );
}

function ExportCard({
  title,
  description,
  disabled,
  onClick,
}: {
  title: string;
  description: string;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="flex items-start gap-3 border border-[#27272A] bg-[#18181B] p-3 text-left transition-colors hover:border-zinc-600 disabled:opacity-40"
    >
      <Download className="mt-0.5 h-4 w-4 shrink-0 text-[#3B82F6]" />
      <div>
        <p className="text-[11px] font-medium text-zinc-200">{title}</p>
        <p className="mt-0.5 text-[10px] text-zinc-600">{description}</p>
      </div>
    </button>
  );
}
