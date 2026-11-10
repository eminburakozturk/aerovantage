"use client";

import { BarChart } from "@tremor/react";

import { OpsPanel } from "@/components/ops/ops-panel";
import { useTranslations } from "@/context/locale-context";
import type { SystemKpiResponse } from "@/lib/api";
import { formatCurrencyTl } from "@/lib/format";

interface MarketFeedPanelProps {
  kpi: SystemKpiResponse | null;
  imbalanceCost?: number;
}

export function MarketFeedPanel({ kpi, imbalanceCost }: MarketFeedPanelProps) {
  const { t } = useTranslations("ui");
  const pipelineRuns = kpi?.pipeline_run_count ?? 0;
  const mape = kpi?.average_mape ?? 0;

  const barData = [
    { metrik: "MAPE", deger: mape },
    { metrik: t("market.uptimeMetric"), deger: kpi?.uptime_percentage ?? 0 },
    { metrik: "API", deger: kpi?.api_availability_percentage ?? 0 },
    { metrik: "Run", deger: Math.min(pipelineRuns * 10, 100) },
  ];

  return (
    <OpsPanel title={t("market.marketKpiFeedTitle")} meta={t("market.epiasSystemMeta")} className="h-full" noPadding>
      <div className="flex h-full flex-col p-2">
        <div className="mb-1 flex shrink-0 items-baseline justify-between">
          <span className="font-mono text-sm text-zinc-200">
            {formatCurrencyTl(imbalanceCost)}
          </span>
          <span className="text-[9px] text-zinc-600">{t("market.imbalanceCostLabel")}</span>
        </div>
        {kpi ? (
          <BarChart
            className="ops-chart min-h-0 flex-1"
            data={barData}
            index="metrik"
            categories={["deger"]}
            colors={["blue"]}
            showLegend={false}
            showYAxis={false}
            showXAxis
            valueFormatter={(v) => `${v.toFixed(0)}`}
          />
        ) : (
          <p className="flex flex-1 items-center justify-center text-[10px] text-zinc-600">
            {t("market.kpiLoading")}
          </p>
        )}
      </div>
    </OpsPanel>
  );
}
