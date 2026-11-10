"use client";

import { useEffect, useState } from "react";
import { BarChart, LineChart } from "@tremor/react";

import { ProductionChart } from "@/components/ops/dashboard/production-chart";
import { AnnotatedKpiCell } from "@/components/ai/annotated-kpi-cell";
import { AiInlineHint } from "@/components/ai/ai-inline-hint";
import { useAnnotations } from "@/components/ai/annotations-context";
import { KpiCell } from "@/components/ops/kpi-cell";
import { OpsPanel } from "@/components/ops/ops-panel";
import { EmptyState, ErrorBanner, LoadingBlock } from "@/components/ui/async-state";
import { useNavConfig } from "@/hooks/use-nav-config";
import { useOperasyon } from "@/context/operasyon-context";
import { useTranslations } from "@/context/locale-context";
import type { BriefingAnnotation, DashboardData, PipelineHistoryEntry } from "@/lib/api";
import { fetchWeatherForecast, type WeatherForecastResponse } from "@/lib/api";
import { formatTimeShort } from "@/lib/format";
import { dedupeHistoryByAssetDate } from "@/lib/history-utils";
import { cn } from "@/lib/utils";
import { STATUS_COLORS, type StatusLevel } from "@/lib/status-level";

interface ForecastWorkspaceProps {
  tab: string;
  data: DashboardData | null;
  history: PipelineHistoryEntry[];
  loading: boolean;
  error: string | null;
}

interface DeviationRow {
  id: string;
  time: string;
  forecast: number;
  actual: number;
  deltaMw: number;
  deltaPct: number;
  status: StatusLevel;
}

function buildDeviationRows(hours: DashboardData["hourlyProduction"]): DeviationRow[] {
  return (hours ?? []).map((h, i) => {
    const deltaMw = h.actual_mw - h.forecast_mw;
    const base = h.forecast_mw !== 0 ? Math.abs(h.forecast_mw) : 1;
    const deltaPct = (deltaMw / base) * 100;
    const abs = Math.abs(deltaMw);
    const status: StatusLevel = abs > 8 ? "crit" : abs > 5 ? "warn" : "normal";
    return {
      id: `h-${i}`,
      time: formatTimeShort(h.timestamp),
      forecast: h.forecast_mw,
      actual: h.actual_mw,
      deltaMw,
      deltaPct,
      status,
    };
  });
}

function confidenceBand(forecastMw: number, mapePct: number) {
  const margin = forecastMw * (mapePct / 100);
  return {
    lower: Math.max(0, forecastMw - margin),
    upper: forecastMw + margin,
    margin,
  };
}

export function ForecastWorkspace({ tab, data, history, loading, error }: ForecastWorkspaceProps) {
  if (error) return <ErrorBanner message={error} />;

  switch (tab) {
    case "weather":
      return <WeatherTab data={data} loading={loading} />;
    case "accuracy":
      return <AccuracyTab data={data} history={history} loading={loading} />;
    case "history":
      return <HistoryTab history={history} loading={loading} />;
    default:
      return <OverviewTab data={data} loading={loading} />;
  }
}

function OverviewTab({ data, loading }: { data: DashboardData | null; loading: boolean }) {
  const { formatStep } = useNavConfig();
  const { t } = useTranslations("ui");
  const lastHour = data?.hourlyProduction?.[data.hourlyProduction.length - 1];
  const delta = lastHour ? lastHour.actual_mw - lastHour.forecast_mw : 0;
  const confidence = data ? Math.max(0, 100 - data.riskScore) : 0;
  const mape = data?.liveMapePercentage ?? 0;
  const forecastMw = data?.forecastMw ?? 0;
  const band = confidenceBand(forecastMw, mape || 15);
  const { getKpi, loading: aiLoading } = useAnnotations();
  const deviationRows = buildDeviationRows(data?.hourlyProduction ?? []);
  const flaggedRows = deviationRows.filter((r) => r.status !== "normal");

  return (
    <div className="space-y-2">
      <section className="grid grid-cols-2 gap-1 md:grid-cols-5">
        <AnnotatedKpiCell kpiId="forecast" label={t("forecast.forecast")} value={loading ? "—" : forecastMw.toFixed(1)} unit="MW" />
        <AnnotatedKpiCell kpiId="production" label={t("forecast.actual")} value={loading ? "—" : (lastHour?.actual_mw.toFixed(1) ?? "—")} unit="MW" />
        <AnnotatedKpiCell kpiId="forecast_deviation" label={t("forecast.deviation")} value={loading ? "—" : delta.toFixed(1)} unit="MW" status={Math.abs(delta) > 5 ? "warn" : "neutral"} />
        <AnnotatedKpiCell kpiId="live_mape" label={t("forecast.mape")} value={loading ? "—" : mape.toFixed(1)} unit="%" status={mape > 18 ? "crit" : mape > 15 ? "warn" : "neutral"} />
        <AnnotatedKpiCell kpiId="risk" label={t("forecast.confidence")} value={loading ? "—" : String(confidence)} unit="%" status={confidence >= 60 ? "neutral" : "warn"} />
      </section>

      <OpsPanel
        title={t("forecast.deviationAnalysis")}
        meta={t("forecast.deviationMeta", { flagged: flaggedRows.length, total: deviationRows.length })}
        density="comfortable"
        className="min-h-[200px]"
      >
        <DeviationTable rows={deviationRows} loading={loading} aiLoading={aiLoading} annotation={getKpi("forecast_deviation")} />
      </OpsPanel>

      <div className="grid gap-2 lg:grid-cols-2">
        <OpsPanel title={t("forecast.confidenceBand")} meta={t("forecast.confidenceBandMeta", { value: mape.toFixed(1) })}>
          <div className="space-y-2 font-mono text-[11px]">
            <Row label={t("forecast.forecast")} value={`${forecastMw.toFixed(1)} MW`} />
            <Row label={t("forecast.lowerBound")} value={`${band.lower.toFixed(1)} MW`} />
            <Row label={t("forecast.upperBound")} value={`${band.upper.toFixed(1)} MW`} />
            <Row label={t("forecast.margin")} value={`±${band.margin.toFixed(1)} MW`} warn={band.margin > 5} />
            <Row label={t("forecast.targetDate")} value={data?.targetDate ?? "—"} />
          </div>
          <AiInlineHint annotation={getKpi("live_mape")} loading={aiLoading} compact />
        </OpsPanel>

        <OpsPanel title={t("forecast.modelPerf")} meta={t("forecast.pipelineStageMeta")}>
          {data?.stepsCompleted.length ? (
            <ol className="space-y-1">
              {data.stepsCompleted.map((step) => (
                <li key={step} className="flex items-center gap-2 text-[10px] text-zinc-400">
                  <span className="h-1 w-1 shrink-0 bg-zinc-500" />
                  {formatStep(step)}
                </li>
              ))}
            </ol>
          ) : (
            <p className="text-[10px] text-zinc-600">{t("forecast.pipelineNotRun")}</p>
          )}
          <AiInlineHint annotation={getKpi("forecast")} loading={aiLoading} compact />
        </OpsPanel>
      </div>

      <OpsPanel title={t("forecast.productionChart")} meta={t("commonUi.secondaryView")}>
        <div className="h-[160px]">
          <ProductionChart data={data} compact />
        </div>
      </OpsPanel>
    </div>
  );
}

function DeviationTable({
  rows,
  loading,
  aiLoading,
  annotation,
}: {
  rows: DeviationRow[];
  loading: boolean;
  aiLoading: boolean;
  annotation?: BriefingAnnotation;
}) {
  const { t } = useTranslations("ui");
  if (loading) return <p className="text-[10px] text-zinc-600">{t("forecast.deviationLoading")}</p>;
  if (!rows.length) return <p className="text-[10px] text-zinc-600">{t("forecast.noHourlyRunPipeline")}</p>;

  return (
    <div className="overflow-auto">
      <table className="w-full text-left text-[10px]">
        <thead className="border-b border-[#27272A] text-[9px] uppercase tracking-wider text-zinc-600">
          <tr>
            <th className="px-2 py-1.5">{t("forecast.hour")}</th>
            <th className="px-2 py-1.5">{t("forecast.forecast")}</th>
            <th className="px-2 py-1.5">{t("forecast.actual")}</th>
            <th className="px-2 py-1.5">{t("forecast.deviation")}</th>
            <th className="px-2 py-1.5">%</th>
            <th className="px-2 py-1.5">{t("ops.status")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const colors = STATUS_COLORS[row.status];
            return (
              <tr key={row.id} className={cn("border-b border-[#27272A]/50 font-mono", row.status !== "normal" && "bg-[#141416]")}>
                <td className="px-2 py-1.5 text-zinc-500">{row.time}</td>
                <td className="px-2 py-1.5 text-zinc-400">{row.forecast.toFixed(1)}</td>
                <td className="px-2 py-1.5 text-zinc-300">{row.actual.toFixed(1)}</td>
                <td className={cn("px-2 py-1.5", row.deltaMw >= 0 ? "text-zinc-300" : "text-rose-400")}>
                  {row.deltaMw >= 0 ? "+" : ""}
                  {row.deltaMw.toFixed(1)}
                </td>
                <td className="px-2 py-1.5 text-zinc-500">{row.deltaPct >= 0 ? "+" : ""}{row.deltaPct.toFixed(1)}</td>
                <td className={cn("px-2 py-1.5 font-sans font-semibold uppercase", colors.text)}>
                  {t(`status.${row.status}`)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <AiInlineHint annotation={annotation} loading={aiLoading} compact className="mt-2 px-2" />
    </div>
  );
}

function WeatherTab({ data, loading }: { data: DashboardData | null; loading: boolean }) {
  const { selectedAssetId } = useOperasyon();
  const { t } = useTranslations("ui");
  const [weather, setWeather] = useState<WeatherForecastResponse | null>(null);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [weatherError, setWeatherError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedAssetId) return;
    let cancelled = false;
    setWeatherLoading(true);
    setWeatherError(null);
    void fetchWeatherForecast(selectedAssetId, data?.targetDate)
      .then((result) => {
        if (!cancelled) setWeather(result);
      })
      .catch((err) => {
        if (!cancelled) {
          setWeather(null);
          setWeatherError(err instanceof Error ? err.message : t("forecast.weatherEmpty"));
        }
      })
      .finally(() => {
        if (!cancelled) setWeatherLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedAssetId, data?.targetDate, t]);

  const windKey = t("forecast.wind");
  const tempKey = t("forecast.temperature");
  const windData =
    weather?.hours.map((h) => ({
      saat: formatTimeShort(h.timestamp),
      [windKey]: h.wind_speed,
      [tempKey]: h.temperature,
    })) ?? [];

  const hours = data?.hourlyProduction ?? [];

  return (
    <div className="space-y-2">
      <section className="grid grid-cols-3 border border-[#27272A] bg-[#18181B]">
        <KpiCell label={t("forecast.hourlyRecords")} value={loading ? "—" : String(hours.length)} />
        <KpiCell label={t("forecast.avgProduction")} value={loading ? "—" : avg(hours.map((h) => h.actual_mw)).toFixed(1)} unit="MW" />
        <KpiCell label={t("forecast.avgForecast")} value={loading ? "—" : avg(hours.map((h) => h.forecast_mw)).toFixed(1)} unit="MW" />
      </section>

      <OpsPanel title={t("forecast.hourlyDetail")} meta={t("forecast.hourlyDetailMeta")}>
        <div className="max-h-[280px] overflow-y-auto">
          <table className="w-full text-[10px]">
            <thead>
              <tr className="border-b border-[#27272A] text-left text-zinc-600">
                <th className="pb-1 pr-2">{t("forecast.hour")}</th>
                <th className="pb-1 pr-2">{t("forecast.forecast")}</th>
                <th className="pb-1 pr-2">{t("forecast.actual")}</th>
                <th className="pb-1">{t("forecast.ptf")}</th>
              </tr>
            </thead>
            <tbody>
              {hours.map((h, i) => (
                <tr key={i} className="border-b border-[#27272A]/50 font-mono text-zinc-400">
                  <td className="py-1 pr-2">{formatTimeShort(h.timestamp)}</td>
                  <td className="py-1 pr-2">{h.forecast_mw.toFixed(1)}</td>
                  <td className="py-1 pr-2">{h.actual_mw.toFixed(1)}</td>
                  <td className="py-1">{h.ptf_price?.toFixed(0) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </OpsPanel>

      <OpsPanel title={t("forecast.windProfile")} meta={t("forecast.windProfileMeta", { source: weather?.source ?? "Open-Meteo" })}>
        {weatherLoading ? (
          <LoadingBlock label={t("forecast.weatherLoading")} rows={2} />
        ) : windData.length > 0 ? (
          <LineChart className="ops-chart h-[140px]" data={windData} index="saat" categories={[windKey, tempKey]} colors={["blue", "slate"]} showLegend={false} showYAxis showXAxis />
        ) : (
          <EmptyState message={weatherError ?? t("forecast.weatherEmpty")} />
        )}
      </OpsPanel>
    </div>
  );
}

function AccuracyTab({ data, history, loading }: { data: DashboardData | null; history: PipelineHistoryEntry[]; loading: boolean }) {
  const { getKpi, loading: aiLoading } = useAnnotations();
  const { t } = useTranslations("ui");
  const mapeHistory = dedupeHistoryByAssetDate(history)
    .filter((h) => h.mape_percentage != null)
    .slice(0, 10)
    .map((h, i) => ({
      id: `${h.asset_id ?? "asset"}-${h.target_date ?? "date"}-${h.saved_at ?? i}`,
      date: h.target_date ?? "—",
      mape: h.mape_percentage ?? 0,
      risk: h.risk_score ?? 0,
      status: ((h.mape_percentage ?? 0) > 18 ? "crit" : (h.mape_percentage ?? 0) > 15 ? "warn" : "normal") as StatusLevel,
    }))
    .sort((a, b) => a.date.localeCompare(b.date));

  const hours = data?.hourlyProduction ?? [];
  const hourlyAccuracy = hours.map((h, i) => {
    const err = Math.abs(h.actual_mw - h.forecast_mw);
    const pct = h.forecast_mw !== 0 ? (err / Math.abs(h.forecast_mw)) * 100 : 0;
    return {
      id: `acc-${i}`,
      time: formatTimeShort(h.timestamp),
      errorMw: err,
      errorPct: pct,
      status: (pct > 20 ? "crit" : pct > 12 ? "warn" : "normal") as StatusLevel,
    };
  });

  return (
    <div className="space-y-2">
      <section className="grid grid-cols-2 gap-1 md:grid-cols-4">
        <AnnotatedKpiCell kpiId="live_mape" label={t("forecast.avgMape")} value={loading ? "—" : (data?.averageMape.toFixed(1) ?? "—")} unit="%" status={(data?.averageMape ?? 0) > 18 ? "crit" : (data?.averageMape ?? 0) > 15 ? "warn" : "neutral"} />
        <AnnotatedKpiCell kpiId="live_mape" label={t("forecast.liveMape")} value={loading ? "—" : (data?.liveMapePercentage.toFixed(1) ?? "—")} unit="%" />
        <KpiCell label={t("forecast.records")} value={loading ? "—" : String(mapeHistory.length)} sub={t("commonUi.daysUnit")} />
        <KpiCell label={t("forecast.status")} value={loading ? "—" : (data?.averageMape ?? 0) <= 15 ? t("forecast.good") : t("forecast.attention")} status={(data?.averageMape ?? 0) > 15 ? "warn" : "neutral"} />
      </section>

      <OpsPanel title={t("forecast.periodAccuracy")} meta={t("forecast.periodAccuracyMeta")} density="comfortable">
        {mapeHistory.length > 0 ? (
          <table className="w-full text-[10px]">
            <thead className="border-b border-[#27272A] text-[9px] uppercase text-zinc-600">
              <tr>
                <th className="px-2 py-1.5 text-left">{t("forecast.date")}</th>
                <th className="px-2 py-1.5 text-left">{t("forecast.mape")}</th>
                <th className="px-2 py-1.5 text-left">{t("forecast.risk")}</th>
                <th className="px-2 py-1.5 text-left">{t("ops.status")}</th>
              </tr>
            </thead>
            <tbody>
              {mapeHistory.map((row) => (
                <tr key={row.id} className="border-b border-[#27272A]/50 font-mono">
                  <td className="px-2 py-1.5 text-zinc-500">{row.date}</td>
                  <td className="px-2 py-1.5 text-zinc-300">%{row.mape.toFixed(1)}</td>
                  <td className="px-2 py-1.5 text-zinc-400">{row.risk}</td>
                  <td className={cn("px-2 py-1.5 font-sans font-semibold uppercase", STATUS_COLORS[row.status].text)}>
                    {t(`status.${row.status}`)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <EmptyState message={t("forecast.noMapeHistory")} />
        )}
        <AiInlineHint annotation={getKpi("live_mape")} loading={aiLoading} compact className="mt-2" />
      </OpsPanel>

      <OpsPanel title={t("forecast.hourlyError")} meta={t("forecast.accuracyBreakdownMeta")} density="comfortable">
        {hourlyAccuracy.length > 0 ? (
          <table className="w-full text-[10px]">
            <thead className="border-b border-[#27272A] text-[9px] uppercase text-zinc-600">
              <tr>
                <th className="px-2 py-1.5 text-left">{t("forecast.hour")}</th>
                <th className="px-2 py-1.5 text-left">{t("forecast.errorMwHeader")}</th>
                <th className="px-2 py-1.5 text-left">{t("forecast.errorPctHeader")}</th>
                <th className="px-2 py-1.5 text-left">{t("ops.status")}</th>
              </tr>
            </thead>
            <tbody>
              {hourlyAccuracy.filter((r) => r.status !== "normal").slice(0, 12).map((row) => (
                <tr key={row.id} className="border-b border-[#27272A]/50 font-mono">
                  <td className="px-2 py-1.5 text-zinc-500">{row.time}</td>
                  <td className="px-2 py-1.5 text-zinc-300">{row.errorMw.toFixed(1)}</td>
                  <td className="px-2 py-1.5 text-zinc-400">%{row.errorPct.toFixed(1)}</td>
                  <td className={cn("px-2 py-1.5 font-sans font-semibold uppercase", STATUS_COLORS[row.status].text)}>
                    {t(`status.${row.status}`)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <EmptyState message={t("forecast.noHourlyErrorFound")} />
        )}
      </OpsPanel>

      <div className="grid gap-2 lg:grid-cols-2">
        <OpsPanel title={t("forecast.mapeTrend")} meta={t("commonUi.secondary")}>
          {mapeHistory.length > 0 ? (
            <BarChart className="ops-chart h-[130px]" data={mapeHistory.map((r) => ({ tarih: r.date, MAPE: r.mape }))} index="tarih" categories={["MAPE"]} colors={["blue"]} showLegend={false} showYAxis showXAxis />
          ) : null}
        </OpsPanel>
        <OpsPanel title={t("forecast.errorHistogram")} meta={t("commonUi.secondary")}>
          {hourlyAccuracy.length > 0 ? (
            <BarChart
              className="ops-chart h-[130px]"
              data={hourlyAccuracy.map((r) => ({ saat: r.time, [t("forecast.errorSeries")]: r.errorMw }))}
              index="saat"
              categories={[t("forecast.errorSeries")]}
              colors={["slate"]}
              showLegend={false}
              showYAxis
              showXAxis
            />
          ) : null}
        </OpsPanel>
      </div>
    </div>
  );
}

function HistoryTab({ history, loading }: { history: PipelineHistoryEntry[]; loading: boolean }) {
  const { t, bcp47 } = useTranslations("ui");
  return (
    <OpsPanel title={t("forecast.historyTitle")} meta={t("forecast.historyMeta", { count: history.length })}>
      <div className="overflow-x-auto">
        <table className="w-full text-[10px]">
          <thead>
            <tr className="border-b border-[#27272A] text-left text-zinc-600">
              <th className="pb-2 pr-3">{t("risk.plant")}</th>
              <th className="pb-2 pr-3">{t("forecast.date")}</th>
              <th className="pb-2 pr-3">{t("forecast.mape")}</th>
              <th className="pb-2 pr-3">{t("forecast.risk")}</th>
              <th className="pb-2 pr-3">{t("commonUi.production")}</th>
              <th className="pb-2">{t("commonUi.cost")}</th>
            </tr>
          </thead>
          <tbody>
            {history.map((entry, i) => (
              <tr key={i} className="border-b border-[#27272A]/50 text-zinc-400">
                <td className="py-2 pr-3">{entry.asset_name ?? entry.asset_id}</td>
                <td className="py-2 pr-3 font-mono">{entry.target_date}</td>
                <td className="py-2 pr-3 font-mono">%{entry.mape_percentage?.toFixed(1) ?? "—"}</td>
                <td className="py-2 pr-3 font-mono">{entry.risk_score ?? "—"}</td>
                <td className="py-2 pr-3 font-mono">{entry.total_daily_mw?.toFixed(1) ?? "—"} MW</td>
                <td className="py-2 font-mono">{entry.total_imbalance_cost_tl?.toLocaleString(bcp47) ?? "—"} TL</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && history.length === 0 ? (
          <EmptyState message={t("forecast.historyEmpty")} />
        ) : null}
      </div>
    </OpsPanel>
  );
}

function Row({ label, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <div className="flex justify-between gap-2">
      <span className="text-zinc-600">{label}</span>
      <span className={cn("text-zinc-200", warn && "text-amber-400")}>{value}</span>
    </div>
  );
}

function avg(nums: number[]) {
  if (!nums.length) return 0;
  return nums.reduce((a, b) => a + b, 0) / nums.length;
}
