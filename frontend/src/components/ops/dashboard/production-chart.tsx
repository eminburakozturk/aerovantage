"use client";

import { LineChart } from "@tremor/react";

import { OpsPanel } from "@/components/ops/ops-panel";
import { useLocale, useTranslations } from "@/context/locale-context";
import type { DashboardData } from "@/lib/api";
import { cn } from "@/lib/utils";

interface ProductionChartProps {
  data: DashboardData | null;
  compact?: boolean;
  className?: string;
}

function buildHourlyChart(
  data: DashboardData | null,
  bcp47: string,
  forecastKey: string,
  actualKey: string,
) {
  const hours = data?.hourlyProduction ?? [];
  if (hours.length === 0) return [];

  return hours.map((hour) => {
    const time = hour.timestamp
      ? new Date(hour.timestamp).toLocaleTimeString(bcp47, {
          hour: "2-digit",
          minute: "2-digit",
        })
      : "—";
    return {
      saat: time,
      [forecastKey]: hour.forecast_mw,
      [actualKey]: hour.actual_mw,
      PTF: hour.ptf_price ?? 0,
    };
  });
}

export function ProductionChart({ data, compact, className }: ProductionChartProps) {
  const { t } = useTranslations("ui");
  const { bcp47 } = useLocale();
  const forecastKey = t("forecast.forecastSeries");
  const actualKey = t("forecast.actualSeries");
  const chartData = buildHourlyChart(data, bcp47, forecastKey, actualKey);
  const forecastMw = data?.forecastMw ?? 0;
  const lastHour = data?.hourlyProduction?.[data.hourlyProduction.length - 1];
  const actualMw = lastHour?.actual_mw ?? forecastMw;

  return (
    <OpsPanel
      title={t("ops.forecastVsActual")}
      meta={t("ops.chartMeta", {
        asset: data?.assetName ?? "—",
        forecast: forecastMw.toFixed(1),
        actual: actualMw.toFixed(1),
      })}
      className={cn("h-full", className)}
      noPadding
      density={compact ? "default" : "comfortable"}
    >
      <div className={compact ? "flex h-full flex-col p-1.5" : "flex h-full flex-col p-2"}>
        <div className={`mb-1.5 flex shrink-0 gap-3 border-b border-[#27272A] ${compact ? "pb-1.5" : "pb-2"}`}>
          <LegendDot color="#93C5FD" label={t("ops.forecastMw")} />
          <LegendDot color="#FFFFFF" label={t("ops.scadaMw")} />
          <LegendDot color="#A1A1AA" label={t("ops.ptfPrice")} />
        </div>
        {chartData.length > 0 ? (
          <LineChart
            className="ops-chart ops-chart-scada h-full min-h-0 flex-1"
            data={chartData}
            index="saat"
            categories={[forecastKey, actualKey, "PTF"]}
            colors={["blue", "slate", "gray"]}
            valueFormatter={(v) => `${v.toFixed(1)}`}
            showLegend={false}
            showYAxis
            showXAxis
            yAxisWidth={36}
            curveType="monotone"
            connectNulls
          />
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center gap-1 text-center">
            <p className="text-[11px] text-zinc-500">{t("ops.noHourlyProduction")}</p>
            <p className="text-[10px] text-zinc-600">{t("ops.runPipelineHint")}</p>
          </div>
        )}
      </div>
    </OpsPanel>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-[9px] text-zinc-500">
      <span className="h-1.5 w-3" style={{ backgroundColor: color }} />
      {label}
    </span>
  );
}
