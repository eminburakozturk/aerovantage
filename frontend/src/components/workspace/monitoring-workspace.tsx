"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ObservabilityTab } from "@/components/monitoring/observability-panel";
import { SystemHealthPanel } from "@/components/ops/dashboard/system-health-panel";
import { KpiCell } from "@/components/ops/kpi-cell";
import { OpsPanel } from "@/components/ops/ops-panel";
import { EmptyState, ErrorBanner, LoadingBlock } from "@/components/ui/async-state";
import { useTranslations } from "@/context/locale-context";
import type { HealthResponse, PipelineHistoryEntry, SystemKpiResponse } from "@/lib/api";
import { fetchJobs, fetchLogs, fetchScheduler, type JobEntry, type LogEntry } from "@/lib/api";
import { getErrorMessage, statusLabel } from "@/lib/user-messages";

interface MonitoringWorkspaceProps {
  tab: string;
  health: HealthResponse | null;
  kpi: SystemKpiResponse | null;
  history: PipelineHistoryEntry[];
  loading: boolean;
  error: string | null;
}

export function MonitoringWorkspace({ tab, health, kpi, history, loading, error }: MonitoringWorkspaceProps) {
  if (error && tab !== "observability") return <ErrorBanner message={error} />;

  switch (tab) {
    case "observability":
      return <ObservabilityTab />;
    case "health":
      return <HealthTab kpi={kpi} loading={loading} />;
    case "jobs":
      return <JobsTab />;
    case "logs":
      return <LogsTab />;
    case "activity":
      return <ActivityTab history={history} loading={loading} />;
    default:
      return <ApiTab health={health} kpi={kpi} loading={loading} />;
  }
}

function ApiTab({ health, kpi, loading }: { health: HealthResponse | null; kpi: SystemKpiResponse | null; loading: boolean }) {
  const { t } = useTranslations("ui");
  return (
    <div className="space-y-2">
      {loading ? <LoadingBlock label={t("monitoring.kpiLoading")} rows={2} /> : null}
      <section className="grid grid-cols-2 border border-[#27272A] bg-[#18181B] md:grid-cols-4">
        <KpiCell label={t("monitoring.apiStatus")} value={loading ? "—" : health?.status === "ok" ? t("monitoring.active") : t("monitoring.error")} status={health?.status === "ok" ? "neutral" : "warn"} />
        <KpiCell label={t("monitoring.uptime")} value={loading ? "—" : (kpi?.uptime_percentage.toFixed(1) ?? "—")} unit="%" status="neutral" />
        <KpiCell label={t("monitoring.apiAccess")} value={loading ? "—" : (kpi?.api_availability_percentage.toFixed(1) ?? "—")} unit="%" />
        <KpiCell label={t("commonUi.pipeline")} value={loading ? "—" : String(kpi?.pipeline_run_count ?? 0)} sub={t("commonUi.runsUnit")} />
      </section>

      <div className="grid gap-2 lg:grid-cols-2">
        <SystemHealthPanel health={health} loading={loading} />
        <OpsPanel title={t("monitoring.dataSources")} meta={t("monitoring.integrationStatusMeta")} density="comfortable">
          {kpi ? (
            <ul className="space-y-0">
              {Object.entries(kpi.data_hub).map(([name, hub]) => (
                <li key={name} className="ops-row-hover flex items-center justify-between border-b border-[#27272A] py-2 text-[11px] last:border-0">
                  <span className="text-zinc-400">{name}</span>
                  <span className="font-mono text-zinc-400">{statusLabel(hub.status)}</span>
                  {hub.mode ? <span className="font-mono text-[9px] text-zinc-600">{hub.mode}</span> : null}
                </li>
              ))}
            </ul>
          ) : loading ? (
            <LoadingBlock label={t("monitoring.kpiLoading")} rows={3} />
          ) : (
            <EmptyState title={t("commonUi.empty")} message={t("monitoring.systemKpiUnavailable")} />
          )}
        </OpsPanel>
      </div>
    </div>
  );
}

function HealthTab({ kpi, loading }: { kpi: SystemKpiResponse | null; loading: boolean }) {
  const { t } = useTranslations("ui");
  return (
    <div className="space-y-2">
      <section className="grid grid-cols-2 border border-[#27272A] bg-[#18181B] md:grid-cols-4">
        <KpiCell label={t("monitoring.uptime")} value={loading ? "—" : (kpi?.uptime_percentage.toFixed(1) ?? "—")} unit="%" status="neutral" />
        <KpiCell label="API" value={loading ? "—" : (kpi?.api_availability_percentage.toFixed(1) ?? "—")} unit="%" />
        <KpiCell label={t("forecast.mape")} value={loading ? "—" : (kpi?.average_mape.toFixed(1) ?? "—")} unit="%" />
        <KpiCell label={t("monitoring.period")} value={loading ? "—" : String(kpi?.period_days ?? 30)} unit={t("commonUi.daysUnit")} />
      </section>

      <OpsPanel title={t("monitoring.systemMetrics")} meta={t("monitoring.lastNDaysMeta", { days: kpi?.period_days ?? 30 })} density="comfortable">
        {loading ? (
          <LoadingBlock rows={2} />
        ) : kpi ? (
          <div className="grid gap-3 sm:grid-cols-2">
            <MetricBlock label={t("monitoring.pipelineRuns")} value={String(kpi.pipeline_run_count)} />
            <MetricBlock label={t("forecast.avgMape")} value={`%${kpi.average_mape.toFixed(1)}`} />
            <MetricBlock label={t("monitoring.uptime")} value={`%${kpi.uptime_percentage.toFixed(1)}`} />
            <MetricBlock label={t("monitoring.apiAvailability")} value={`%${kpi.api_availability_percentage.toFixed(1)}`} />
          </div>
        ) : (
          <EmptyState title={t("monitoring.noMetrics")} message={t("monitoring.metricsNotYetGenerated")} />
        )}
      </OpsPanel>
    </div>
  );
}

function JobsTab() {
  const { t, locale } = useTranslations("ui");
  const [jobs, setJobs] = useState<JobEntry[]>([]);
  const [scheduler, setScheduler] = useState<Awaited<ReturnType<typeof fetchScheduler>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    void Promise.all([fetchJobs(15), fetchScheduler(locale)])
      .then(([j, s]) => {
        setJobs(j);
        setScheduler(s);
      })
      .catch((err) => setError(getErrorMessage(err, t("monitoring.jobQueueFetchFailed"))))
      .finally(() => setLoading(false));
  }, [t, locale]);

  if (loading) return <LoadingBlock label={t("monitoring.schedulerJobsLoading")} rows={4} />;
  if (error) return <ErrorBanner message={error} />;

  return (
    <div className="space-y-2">
      <OpsPanel title={t("monitoring.scheduler")} meta={scheduler?.timezone} density="comfortable">
        {scheduler?.jobs.length ? (
          scheduler.jobs.map((job) => (
            <div key={job.id} className="ops-surface-interactive mb-2 p-3 text-[11px]">
              <p className="text-zinc-200">{job.name}</p>
              <p className="text-zinc-500">{job.schedule} · {statusLabel(job.status)}</p>
              <p className="font-mono text-[10px] text-zinc-600">{t("monitoring.lastRunPrefix")} {job.last_run ?? "—"}</p>
            </div>
          ))
        ) : (
          <EmptyState title={t("monitoring.noSchedulerRecords")} message={t("monitoring.noScheduledJobsMessage")} />
        )}
      </OpsPanel>
      <OpsPanel title={t("monitoring.backgroundJobs")} meta={t("commonUi.recordsMeta", { count: jobs.length })} density="comfortable">
        {jobs.length ? (
          jobs.map((job) => (
            <div key={job.job_id} className="ops-row-hover flex justify-between border-b border-[#27272A] py-2 text-[11px] last:border-0">
              <span className="text-zinc-400">{job.asset_id}</span>
              <span className="font-mono text-zinc-500">{statusLabel(job.status)}</span>
            </div>
          ))
        ) : (
          <EmptyState title={t("monitoring.noJobRecords")} message={t("monitoring.noBackgroundJobsMessage")} />
        )}
      </OpsPanel>
    </div>
  );
}

function LogsTab() {
  const { t, locale } = useTranslations("ui");
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    void fetchLogs(80, locale)
      .then(setLogs)
      .catch((err) => setError(getErrorMessage(err, t("monitoring.logsFetchFailed"))))
      .finally(() => setLoading(false));
  }, [t, locale]);

  if (loading) return <LoadingBlock label={t("monitoring.logsLoading")} rows={6} />;
  if (error) return <ErrorBanner message={error} />;

  return (
    <OpsPanel title={t("monitoring.appLogs")} meta={t("monitoring.linesMeta", { count: logs.length })} density="comfortable">
      {logs.length ? (
        <div className="max-h-[400px] overflow-y-auto font-mono text-[10px]">
          {logs.map((log, i) => (
            <div key={i} className="ops-row-hover border-b border-[#27272A]/50 py-1.5">
              <span className="text-zinc-600">{log.timestamp}</span>{" "}
              <span className="text-amber-500">{log.level}</span>{" "}
              <span className="text-zinc-500">{log.message}</span>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState title={t("monitoring.noLogRecords")} message={t("monitoring.noLogsMessage")} />
      )}
    </OpsPanel>
  );
}

function ActivityTab({ history, loading }: { history: PipelineHistoryEntry[]; loading: boolean }) {
  const { t } = useTranslations("ui");
  return (
    <div className="space-y-2">
      <OpsPanel
        title={t("ops.opsFlow")}
        meta={t("monitoring.pipelineAuditMeta")}
        density="comfortable"
        action={
          <Link href="/activity" className="text-[10px] text-[#3B82F6] hover:underline">
            {t("commonUi.fullScreen")} →
          </Link>
        }
      >
        {loading ? (
          <LoadingBlock rows={4} />
        ) : history.length ? (
          <div className="space-y-0">
            {history.slice(0, 12).map((entry, i) => (
              <div key={i} className="ops-row-hover grid gap-2 border-b border-[#27272A] py-2.5 last:border-0 lg:grid-cols-[120px_1fr]">
                <p className="font-mono text-[10px] text-zinc-500">{entry.target_date}</p>
                <p className="text-[11px] text-zinc-400">{entry.ai_insight ?? entry.asset_id}</p>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            title={t("monitoring.noFlowRecords")}
            message={t("monitoring.flowAppearsAfterPipelineMessage")}
          />
        )}
      </OpsPanel>
    </div>
  );
}

function MetricBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="ops-surface p-3">
      <p className="text-[9px] uppercase text-zinc-600">{label}</p>
      <p className="mt-1 font-mono text-lg text-zinc-200">{value}</p>
    </div>
  );
}
