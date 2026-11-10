"use client";

import { useEffect, useState } from "react";
import { BarChart, LineChart } from "@tremor/react";

import { MarketFeedPanel } from "@/components/ops/dashboard/market-feed-panel";
import { KpiCell } from "@/components/ops/kpi-cell";
import { OpsPanel } from "@/components/ops/ops-panel";
import { ErrorBanner } from "@/components/ui/async-state";
import { useTranslations } from "@/context/locale-context";
import type { DashboardData, PipelineHistoryEntry, SystemKpiResponse } from "@/lib/api";
import { fetchSmf, type MarketPriceResponse } from "@/lib/api";
import { formatMape, formatTimeShort } from "@/lib/format";
import { historyTrendRows } from "@/lib/history-utils";

interface MarketWorkspaceProps {
  tab: string;
  data: DashboardData | null;
  history: PipelineHistoryEntry[];
  kpi: SystemKpiResponse | null;
  loading: boolean;
  error: string | null;
}

export function MarketWorkspace({ tab, data, history, kpi, loading, error }: MarketWorkspaceProps) {
  if (error) return <ErrorBanner message={error} />;

  switch (tab) {
    case "ptf":
      return <PtfTab data={data} loading={loading} />;
    case "smf":
      return <SmfTab loading={loading} />;
    case "trends":
      return <TrendsTab history={history} data={data} loading={loading} />;
    default:
      return <OverviewTab data={data} kpi={kpi} loading={loading} />;
  }
}

function OverviewTab({ data, kpi, loading }: { data: DashboardData | null; kpi: SystemKpiResponse | null; loading: boolean }) {
  const { t } = useTranslations("ui");
  const cost = data?.totalImbalanceCostTl ?? 0;
  const imbalanceStatus: "warn" | "neutral" = !data ? "neutral" : cost > 100000 ? "warn" : "neutral";

  return (
    <div className="space-y-2">
      <section className="grid grid-cols-2 border border-[#27272A] bg-[#18181B] md:grid-cols-4">
        <KpiCell label={t("market.imbalance")} value={loading ? "—" : ""} unit="TL" compactCurrency={data?.totalImbalanceCostTl} status={imbalanceStatus} />
        <KpiCell label={t("forecast.liveMape")} value={loading ? "—" : formatMape(data?.liveMapePercentage)} unit="%" />
        <KpiCell label={t("monitoring.uptime")} value={loading ? "—" : (kpi?.uptime_percentage.toFixed(1) ?? "—")} unit="%" />
        <KpiCell label={t("commonUi.pipeline")} value={loading ? "—" : String(kpi?.pipeline_run_count ?? 0)} sub={t("commonUi.runsUnit")} />
      </section>

      <div className="grid gap-2 lg:grid-cols-2">
        <div className="h-[220px]">
          <MarketFeedPanel kpi={kpi} imbalanceCost={data?.totalImbalanceCostTl} />
        </div>
        <OpsPanel title={t("market.marketSummary")} meta={t("market.executiveMeta")}>
          <p className="text-[11px] leading-relaxed text-zinc-300">{data?.executiveSummary ?? "—"}</p>
          <div className="mt-3 grid grid-cols-2 gap-2 border-t border-[#27272A] pt-2">
            <MiniStat label={t("risk.riskScore")} value={String(data?.riskScore ?? "—")} />
            <MiniStat label={t("risk.criticalAlert")} value={String(data?.criticalAlertsCount ?? 0)} />
          </div>
        </OpsPanel>
      </div>
    </div>
  );
}

function PtfTab({ data, loading }: { data: DashboardData | null; loading: boolean }) {
  const { t } = useTranslations("ui");
  const costKey = t("risk.costSeries");
  const ptfData =
    data?.hourlyProduction?.map((h) => ({
      saat: formatTimeShort(h.timestamp),
      PTF: h.ptf_price ?? 0,
      [costKey]: h.imbalance_cost_tl ?? 0,
    })) ?? [];

  const avgPtf = ptfData.length ? ptfData.reduce((s, d) => s + d.PTF, 0) / ptfData.length : 0;
  const maxPtf = ptfData.length ? Math.max(...ptfData.map((d) => d.PTF)) : 0;

  return (
    <div className="space-y-2">
      <section className="grid grid-cols-3 border border-[#27272A] bg-[#18181B]">
        <KpiCell label={t("market.avgPtf")} value={loading ? "—" : avgPtf.toFixed(0)} unit="TL/MWh" />
        <KpiCell label={t("market.maxPtf")} value={loading ? "—" : maxPtf.toFixed(0)} unit="TL/MWh" />
        <KpiCell label={t("market.hour")} value={loading ? "—" : String(ptfData.length)} />
      </section>

      <div className="h-[300px]">
        <OpsPanel title={t("market.epiasPtf")} meta={t("market.hourlyTlMwh")} noPadding className="h-full">
          <div className="flex h-full flex-col p-2">
            {ptfData.length > 0 ? (
              <BarChart className="ops-chart min-h-0 flex-1" data={ptfData} index="saat" categories={["PTF"]} colors={["blue"]} showLegend={false} showYAxis showXAxis />
            ) : (
              <p className="flex flex-1 items-center justify-center text-[10px] text-zinc-600">{t("market.runPipelinePtf")}</p>
            )}
          </div>
        </OpsPanel>
      </div>

      <OpsPanel title={t("market.imbalance")} meta={t("market.hourlyTl")}>
        {ptfData.length > 0 ? (
          <LineChart className="ops-chart h-[160px]" data={ptfData} index="saat" categories={[costKey]} colors={["slate"]} showLegend={false} showYAxis showXAxis />
        ) : null}
      </OpsPanel>
    </div>
  );
}

function SmfTab({ loading }: { loading: boolean }) {
  const { t } = useTranslations("ui");
  const [smf, setSmf] = useState<MarketPriceResponse | null>(null);

  useEffect(() => {
    void fetchSmf().then(setSmf).catch(() => setSmf(null));
  }, []);

  const smfData =
    smf?.hours.map((h) => ({
      saat: `${String(h.hour).padStart(2, "0")}:00`,
      SMF: Number(h.smf ?? 0),
    })) ?? [];

  const avg = smfData.length ? smfData.reduce((s, d) => s + d.SMF, 0) / smfData.length : 0;

  return (
    <div className="space-y-2">
      <section className="grid grid-cols-3 border border-[#27272A] bg-[#18181B]">
        <KpiCell label={t("market.avgSmf")} value={loading ? "—" : avg.toFixed(0)} unit="TL/MWh" />
        <KpiCell label={t("commonUi.source")} value={smf?.source ?? "—"} />
        <KpiCell label={t("forecast.date")} value={smf?.delivery_date ?? "—"} />
      </section>
      <div className="h-[300px]">
        <OpsPanel title={t("market.smfTitle")} meta={t("market.hourlyTlMwh")} noPadding className="h-full">
          <div className="flex h-full flex-col p-2">
            {smfData.length > 0 ? (
              <BarChart className="ops-chart min-h-0 flex-1" data={smfData} index="saat" categories={["SMF"]} colors={["blue"]} showLegend={false} showYAxis showXAxis />
            ) : (
              <p className="flex flex-1 items-center justify-center text-[10px] text-zinc-600">{t("market.smfLoading")}</p>
            )}
          </div>
        </OpsPanel>
      </div>
    </div>
  );
}

function TrendsTab({ history, data, loading }: { history: PipelineHistoryEntry[]; data: DashboardData | null; loading: boolean }) {
  const { t, bcp47 } = useTranslations("ui");
  const costKey = t("risk.costSeries");
  const costTrend = historyTrendRows(history, 12, costKey);

  return (
    <div className="space-y-2">
      <section className="grid grid-cols-2 border border-[#27272A] bg-[#18181B] md:grid-cols-3">
        <KpiCell label={t("market.currentCost")} value={loading ? "—" : (data?.totalImbalanceCostTl.toLocaleString(bcp47) ?? "—")} unit="TL" />
        <KpiCell label={t("market.trendRecords")} value={loading ? "—" : String(costTrend.length)} sub={t("commonUi.daysUnit")} />
        <KpiCell label={t("forecast.risk")} value={loading ? "—" : String(data?.riskScore ?? "—")} unit="/100" />
      </section>

      <div className="h-[280px]">
        <OpsPanel title={t("market.costTrend")} meta={t("market.dailyImbalanceUniqueDayMeta")} noPadding className="h-full">
          <div className="flex h-full flex-col p-2">
            {costTrend.length > 0 ? (
              <LineChart className="ops-chart min-h-0 flex-1" data={costTrend} index="tarih" categories={[costKey]} colors={["blue"]} showLegend={false} showYAxis showXAxis />
            ) : (
              <p className="flex flex-1 items-center justify-center text-[10px] text-zinc-600">{t("market.noTrend")}</p>
            )}
          </div>
        </OpsPanel>
      </div>

      <OpsPanel title={t("market.riskCostCorrelation")} meta={t("commonUi.correlation")}>
        {costTrend.length > 0 ? (
          <LineChart className="ops-chart h-[160px]" data={costTrend} index="tarih" categories={["Risk"]} colors={["slate"]} showLegend={false} showYAxis showXAxis />
        ) : null}
      </OpsPanel>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[9px] text-zinc-600">{label}</p>
      <p className="font-mono text-sm text-zinc-200">{value}</p>
    </div>
  );
}
