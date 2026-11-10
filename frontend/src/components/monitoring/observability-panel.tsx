"use client";

import { useCallback, useEffect, useState } from "react";

import { KpiCell } from "@/components/ops/kpi-cell";
import { OpsPanel } from "@/components/ops/ops-panel";
import { EmptyState, ErrorBanner, LoadingBlock } from "@/components/ui/async-state";
import { useOperasyon } from "@/context/operasyon-context";
import { useTranslations } from "@/context/locale-context";
import {
  type AlertQualityResponse,
  type ConfidenceStackResponse,
  type DegradedSummaryResponse,
  type DriftSummaryResponse,
  type ObservabilitySummaryResponse,
  type RecommendationQualityResponse,
  fetchAlertQuality,
  fetchConfidenceStack,
  fetchDegradedSummary,
  fetchDriftSummary,
  fetchObservabilitySummary,
  fetchRecommendationQuality,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import { getErrorMessage } from "@/lib/user-messages";

type ObsBundle = {
  observability: ObservabilitySummaryResponse;
  degraded: DegradedSummaryResponse;
  drift: DriftSummaryResponse;
  confidence: ConfidenceStackResponse | null;
  alertQuality: AlertQualityResponse | null;
  recommendationQuality: RecommendationQualityResponse | null;
};

function pct(value: number | undefined | null, digits = 1): string {
  if (value == null || Number.isNaN(value)) return "—";
  return (value * 100).toFixed(digits);
}

function num(value: number | undefined | null, digits = 1): string {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

export function ObservabilityTab() {
  const { selectedAssetId } = useOperasyon();
  const { t } = useTranslations("monitoring");
  const [data, setData] = useState<ObsBundle | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const assetId = selectedAssetId || undefined;
      const [observability, degraded, drift] = await Promise.all([
        fetchObservabilitySummary(assetId),
        fetchDegradedSummary(assetId),
        fetchDriftSummary(assetId),
      ]);

      let confidence: ConfidenceStackResponse | null = null;
      let alertQuality: AlertQualityResponse | null = null;
      let recommendationQuality: RecommendationQualityResponse | null = null;

      if (selectedAssetId) {
        const [c, a, r] = await Promise.all([
          fetchConfidenceStack(selectedAssetId).catch(() => null),
          fetchAlertQuality(selectedAssetId).catch(() => null),
          fetchRecommendationQuality(selectedAssetId).catch(() => null),
        ]);
        confidence = c;
        alertQuality = a;
        recommendationQuality = r;
      }

      setData({
        observability,
        degraded,
        drift,
        confidence,
        alertQuality,
        recommendationQuality,
      });
    } catch (err) {
      setError(getErrorMessage(err, t("obs.loadError")));
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [selectedAssetId, t]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) return <LoadingBlock label={t("obs.loading")} rows={5} />;
  if (error) return <ErrorBanner message={error} onRetry={() => void load()} />;
  if (!data) {
    return <EmptyState title={t("obs.emptyTitle")} message={t("obs.emptyMessage")} />;
  }

  const { observability, degraded, drift, confidence, alertQuality, recommendationQuality } = data;
  const mockHeavy = degraded.avg_mock_usage_rate != null && degraded.avg_mock_usage_rate >= 0.5;
  const successRate = observability.api_success.success_rate;
  const coverageRate = observability.coverage.avg_coverage_rate;

  return (
    <div className="space-y-2">
      <section className="grid grid-cols-2 border border-[#27272A] bg-[#18181B] md:grid-cols-3 xl:grid-cols-6">
        <KpiCell
          label={t("obs.degradedRatio")}
          value={num(degraded.degraded_ratio_pct, 1)}
          unit="%"
          status={degraded.degraded_ratio_pct > 50 ? "warn" : "ok"}
          sub={`${degraded.degraded_runs}/${degraded.sample_size} run`}
        />
        <KpiCell
          label={t("obs.mockUsage")}
          value={pct(degraded.avg_mock_usage_rate)}
          unit="%"
          status={mockHeavy ? "warn" : "ok"}
        />
        <KpiCell
          label={t("obs.pipelineSuccess")}
          value={pct(successRate)}
          unit="%"
          status={successRate < 0.9 ? "warn" : "ok"}
          sub={`${observability.api_success.successful_runs}/${observability.api_success.pipeline_runs}`}
        />
        <KpiCell
          label={t("obs.avgLatency")}
          value={num(observability.latency.avg_pipeline_total_ms, 0)}
          unit="ms"
          sub={`${observability.latency.sample_size}`}
        />
        <KpiCell
          label={t("obs.coverage")}
          value={pct(coverageRate)}
          unit="%"
          status={coverageRate > 0 && coverageRate < 0.8 ? "warn" : "ok"}
        />
        <KpiCell
          label={t("obs.driftCrit")}
          value={String(drift.severity_counts.crit)}
          status={drift.severity_counts.crit > 0 ? "crit" : drift.severity_counts.warn > 0 ? "warn" : "ok"}
          sub={`warn ${drift.severity_counts.warn}`}
        />
      </section>

      <div className="grid gap-2 lg:grid-cols-2">
        <OpsPanel title={t("obs.sourceModes")} meta={t("obs.sourceModesMeta")} density="comfortable">
          <div className="space-y-2">
            {(["weather", "scada", "epias", "gemini"] as const).map((source) => {
              const counts = degraded.source_mode_counts[source] ?? {
                live: 0,
                mock: 0,
                simulated: 0,
                fallback: 0,
              };
              const liveRate = observability.source_success_rates[source] ?? 0;
              return (
                <SourceModeRow
                  key={source}
                  name={source}
                  live={counts.live ?? 0}
                  mock={counts.mock ?? 0}
                  simulated={counts.simulated ?? 0}
                  fallback={counts.fallback ?? 0}
                  liveRate={liveRate}
                />
              );
            })}
          </div>
        </OpsPanel>

        <OpsPanel title={t("obs.fallbackReasons")} meta="telemetry" density="comfortable">
          {Object.keys(observability.fallback_reasons).length ||
          Object.keys(degraded.degraded_reason_counts).length ? (
            <ul className="space-y-0">
              {Object.entries({
                ...degraded.degraded_reason_counts,
                ...observability.fallback_reasons,
              })
                .sort((a, b) => b[1] - a[1])
                .slice(0, 8)
                .map(([reason, count]) => (
                  <li
                    key={reason}
                    className="ops-row-hover flex items-center justify-between border-b border-[#27272A] py-2 text-[11px] last:border-0"
                  >
                    <span className="truncate text-zinc-400">{reason}</span>
                    <span className="font-mono text-amber-400">{count}</span>
                  </li>
                ))}
            </ul>
          ) : (
            <EmptyState title={t("obs.fallbackEmptyTitle")} message={t("obs.fallbackEmptyMessage")} />
          )}
        </OpsPanel>
      </div>

      <div className="grid gap-2 lg:grid-cols-2">
        <OpsPanel title={t("obs.driftSummary")} meta={`${drift.sample_size} run`} density="comfortable">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <MiniStat label={t("obs.mapeDrift")} value={String(drift.mape_drift_runs)} />
            <MiniStat label={t("obs.costDrift")} value={String(drift.cost_drift_runs)} />
            <MiniStat label="Z-score" value={String(drift.z_score_detections)} />
            <MiniStat label="Legacy" value={String(drift.legacy_detections)} />
          </div>
          <div className="mt-3 flex gap-2 text-[10px]">
            <SeverityChip label="normal" count={drift.severity_counts.normal} tone="ok" />
            <SeverityChip label="warn" count={drift.severity_counts.warn} tone="warn" />
            <SeverityChip label="crit" count={drift.severity_counts.crit} tone="crit" />
          </div>
        </OpsPanel>

        <OpsPanel
          title={t("obs.stepLatency")}
          meta={`ort. ${num(observability.latency.avg_pipeline_total_ms, 0)} ms`}
          density="comfortable"
        >
          {Object.keys(observability.latency.avg_step_timings_ms).length ? (
            <ul className="space-y-0">
              {Object.entries(observability.latency.avg_step_timings_ms)
                .sort((a, b) => b[1] - a[1])
                .map(([step, ms]) => (
                  <li
                    key={step}
                    className="ops-row-hover flex items-center justify-between border-b border-[#27272A] py-2 text-[11px] last:border-0"
                  >
                    <span className="font-mono text-[10px] text-zinc-500">{step}</span>
                    <span className="font-mono text-zinc-300">{num(ms, 0)} ms</span>
                  </li>
                ))}
            </ul>
          ) : (
            <EmptyState title={t("obs.latencyEmptyTitle")} message={t("obs.latencyEmptyMessage")} />
          )}
        </OpsPanel>
      </div>

      <div className="grid gap-2 lg:grid-cols-3">
        <OpsPanel
          title={t("obs.confidence")}
          meta={selectedAssetId || t("obs.selectAsset")}
          density="comfortable"
        >
          {!selectedAssetId ? (
            <EmptyState title={t("obs.selectAssetTitle")} message={t("obs.selectAssetMessage")} />
          ) : !confidence?.found ? (
            <EmptyState title={t("obs.noRecordTitle")} message={t("obs.noRecordMessage")} />
          ) : (
            <div className="grid grid-cols-2 gap-2">
              <MiniStat label={t("obs.calibrated")} value={pct(confidence.confidence_calibrated)} suffix="%" />
              <MiniStat label={t("obs.coverage")} value={pct(confidence.coverage?.coverage_rate)} suffix="%" />
              <MiniStat
                label={t("obs.interval")}
                value={
                  confidence.prediction_interval
                    ? `${num(confidence.prediction_interval.lower_mw)}–${num(confidence.prediction_interval.upper_mw)}`
                    : "—"
                }
                suffix="MW"
              />
              <MiniStat
                label={t("obs.target")}
                value={confidence.coverage?.meets_target ? "OK" : t("obs.targetLow")}
              />
            </div>
          )}
        </OpsPanel>

        <OpsPanel title={t("obs.alertQuality")} meta={t("obs.days7")} density="comfortable">
          {!alertQuality ? (
            <EmptyState title={t("obs.noDataTitle")} message={t("obs.alertEmpty")} />
          ) : (
            <div className="grid grid-cols-2 gap-2">
              <MiniStat label={t("obs.score")} value={num(alertQuality.quality_score)} />
              <MiniStat label={t("obs.precision")} value={pct(alertQuality.precision_proxy)} suffix="%" />
              <MiniStat label={t("obs.fpRate")} value={pct(alertQuality.false_positive_rate)} suffix="%" />
              <MiniStat label={t("obs.samples")} value={String(alertQuality.samples)} />
            </div>
          )}
        </OpsPanel>

        <OpsPanel title={t("obs.recQuality")} meta={t("obs.days7")} density="comfortable">
          {!recommendationQuality ? (
            <EmptyState title={t("obs.noDataTitle")} message={t("obs.recEmpty")} />
          ) : (
            <div className="grid grid-cols-2 gap-2">
              <MiniStat label={t("obs.score")} value={num(recommendationQuality.quality_score)} />
              <MiniStat
                label={t("obs.actionCoverage")}
                value={pct(recommendationQuality.action_coverage)}
                suffix="%"
              />
              <MiniStat
                label={t("obs.improvement")}
                value={pct(recommendationQuality.improved_after_action_ratio)}
                suffix="%"
              />
              <MiniStat label={t("obs.samples")} value={String(recommendationQuality.samples)} />
            </div>
          )}
        </OpsPanel>
      </div>
    </div>
  );
}

function SourceModeRow({
  name,
  live,
  mock,
  simulated = 0,
  fallback = 0,
  liveRate,
}: {
  name: string;
  live: number;
  mock: number;
  simulated?: number;
  fallback?: number;
  liveRate: number;
}) {
  const total = live + mock + simulated + fallback;
  const livePct = total ? (live / total) * 100 : 0;
  const simPct = total ? (simulated / total) * 100 : 0;
  const fallbackPct = total ? (fallback / total) * 100 : 0;
  const mockPct = total ? (mock / total) * 100 : 0;
  return (
    <div className="border border-[#27272A] bg-[#141416] px-3 py-2">
      <div className="flex items-center justify-between text-[11px]">
        <span className="font-medium text-zinc-300">{name}</span>
        <span className="font-mono text-[10px] text-zinc-500">live %{pct(liveRate, 0)}</span>
      </div>
      <div className="mt-2 flex h-1.5 overflow-hidden bg-[#27272A]">
        <div className="bg-emerald-500/80" style={{ width: `${livePct}%` }} />
        <div className="bg-sky-500/70" style={{ width: `${simPct}%` }} />
        <div className="bg-orange-500/70" style={{ width: `${fallbackPct}%` }} />
        <div className="bg-amber-500/80" style={{ width: `${mockPct}%` }} />
      </div>
      <div className="mt-1.5 flex flex-wrap justify-between gap-x-2 font-mono text-[9px] uppercase text-zinc-600">
        <span>live {live}</span>
        {simulated > 0 ? <span>sim {simulated}</span> : null}
        {fallback > 0 ? <span>fb {fallback}</span> : null}
        <span>mock {mock}</span>
      </div>
    </div>
  );
}

function MiniStat({
  label,
  value,
  suffix,
}: {
  label: string;
  value: string;
  suffix?: string;
}) {
  return (
    <div className="ops-surface p-2.5">
      <p className="text-[9px] uppercase text-zinc-600">{label}</p>
      <p className="mt-1 font-mono text-sm text-zinc-200">
        {value}
        {suffix ? <span className="ml-0.5 text-[10px] text-zinc-500">{suffix}</span> : null}
      </p>
    </div>
  );
}

function SeverityChip({
  label,
  count,
  tone,
}: {
  label: string;
  count: number;
  tone: "ok" | "warn" | "crit";
}) {
  return (
    <span
      className={cn(
        "border px-2 py-1 font-mono uppercase",
        tone === "ok" && "border-emerald-500/30 text-emerald-400",
        tone === "warn" && "border-amber-500/30 text-amber-400",
        tone === "crit" && "border-rose-500/30 text-rose-400",
      )}
    >
      {label} {count}
    </span>
  );
}
