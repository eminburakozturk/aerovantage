"use client";

import Link from "next/link";
import { useMemo } from "react";

import { OpsPanel } from "@/components/ops/ops-panel";
import { ErrorBanner } from "@/components/ui/async-state";
import {
  AiSectionCard,
  ConfidencePill,
  StructuredBriefingCards,
  TechnicalBriefingCards,
} from "@/components/workspace/ai-cards";
import { useContextBriefing } from "@/hooks/use-context-briefing";
import { useDecisionStore } from "@/hooks/use-decision-store";
import { useTranslations } from "@/context/locale-context";
import type { BriefingAnnotation, DashboardData, PipelineHistoryEntry } from "@/lib/api";
import { extractActionableAnnotations } from "@/lib/annotations";
import { dedupeHistoryByAssetDate } from "@/lib/history-utils";
import { cn } from "@/lib/utils";
import { normalizeSeverity, STATUS_COLORS } from "@/lib/status-level";

function resolveTab(tab: string): "pending" | "archive" {
  if (tab === "archive") return "archive";
  if (["history", "brief", "explain", "recommendations"].includes(tab)) return "archive";
  return "pending";
}

interface AiWorkspaceProps {
  tab: string;
  data: DashboardData | null;
  history: PipelineHistoryEntry[];
  loading: boolean;
  error: string | null;
}

export function AiWorkspace({ tab, data, history, loading, error }: AiWorkspaceProps) {
  const { briefing, loading: briefingLoading } = useContextBriefing("ai", 30);
  const isLoading = loading || briefingLoading;

  if (error) {
    return <ErrorBanner message={error} className="m-2" />;
  }

  const activeTab = resolveTab(tab);

  if (activeTab === "archive") {
    return <ArchiveTab briefing={briefing} history={history} loading={isLoading} />;
  }

  return <PendingActionsTab briefing={briefing} data={data} loading={isLoading} />;
}

function PendingActionsTab({
  briefing,
  data,
  loading,
}: {
  briefing: ReturnType<typeof useContextBriefing>["briefing"];
  data: DashboardData | null;
  loading: boolean;
}) {
  const { t } = useTranslations("ui");
  const { setStatus, getStatus, isPending } = useDecisionStore();
  const allActions = useMemo(() => extractActionableAnnotations(briefing), [briefing]);
  const pendingActions = allActions.filter((a) => isPending(a.id));
  const resolvedCount = allActions.length - pendingActions.length;
  const confidence = briefing?.structured?.confidence ?? briefing?.metrics.confidence ?? 0;

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-start justify-between gap-3 border border-[#27272A] border-l-2 border-l-[#3B82F6] bg-[#0C0E14] p-4">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#3B82F6]">{t("risk.decisionCenter")}</p>
          <p className="mt-1 text-[14px] font-medium text-zinc-100">{t("ai.pendingActions")}</p>
          <p className="mt-1 text-[11px] text-zinc-600">
            {data?.assetName ?? briefing?.asset_name ?? t("commonUi.portfolio")} ·{" "}
            {t("ai.pendingSummary", { pending: pendingActions.length, processed: resolvedCount })}
          </p>
        </div>
        <ConfidencePill value={confidence} />
      </header>

      {loading ? (
        <p className="text-[11px] text-zinc-600">{t("ai.actionsLoading")}</p>
      ) : pendingActions.length === 0 ? (
        <OpsPanel title={t("ai.noPendingActions")} meta={t("ai.allProcessed")} density="comfortable">
          <p className="text-[11px] text-zinc-400">{t("ai.allActionsCompleteHint")}</p>
          <Link href="/ai?tab=archive" className="mt-3 inline-block text-[10px] text-[#3B82F6] hover:underline">
            {t("ai.archiveTitle")} →
          </Link>
        </OpsPanel>
      ) : (
        <div className="space-y-2">
          {pendingActions.map((action) => (
            <ActionCard
              key={action.id}
              action={action}
              status={getStatus(action.id)}
              onApprove={() =>
                setStatus(action.id, "approved", {
                  recommendedAction: action.recommended_action,
                  label: action.label,
                  context: action.context,
                })
              }
              onPostpone={() =>
                setStatus(action.id, "postponed", {
                  recommendedAction: action.recommended_action,
                  label: action.label,
                  context: action.context,
                })
              }
              onReject={() =>
                setStatus(action.id, "rejected", {
                  recommendedAction: action.recommended_action,
                  label: action.label,
                  context: action.context,
                })
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ActionCard({
  action,
  status,
  onApprove,
  onPostpone,
  onReject,
}: {
  action: BriefingAnnotation;
  status: string;
  onApprove: () => void;
  onPostpone: () => void;
  onReject: () => void;
}) {
  const { t } = useTranslations("ui");
  const severity = normalizeSeverity(action.severity);
  const colors = STATUS_COLORS[severity];

  return (
    <div className={cn("border border-[#27272A] border-l-2 bg-[#18181B] p-4", colors.border.replace("/40", ""))}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className={cn("text-[9px] font-semibold uppercase tracking-[0.08em]", colors.text)}>
              {t(`status.${severity}`)}
            </span>
            <span className="text-[9px] text-zinc-600">·</span>
            <span className="text-[9px] uppercase tracking-[0.08em] text-zinc-500">{action.label}</span>
            <span className="text-[9px] text-zinc-700">· {action.context}</span>
          </div>
          <p className="mt-2 text-[12px] leading-relaxed text-zinc-300">{action.insight}</p>
          <p className="mt-2 font-mono text-[11px] leading-relaxed text-[#93C5FD]">→ {action.recommended_action}</p>
          <p className="mt-1 text-[9px] text-zinc-600">{t("ai.confidenceValue", { value: action.confidence })}</p>
        </div>
        {status !== "pending" ? (
          <span className="text-[9px] uppercase text-zinc-500">{statusLabel(status, t)}</span>
        ) : null}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <DecisionButton label={t("ai.approve")} tone="emerald" onClick={onApprove} />
        <DecisionButton label={t("ai.postpone")} tone="amber" onClick={onPostpone} />
        <DecisionButton label={t("ai.reject")} tone="rose" onClick={onReject} />
      </div>
    </div>
  );
}

function DecisionButton({
  label,
  tone,
  onClick,
}: {
  label: string;
  tone: "emerald" | "amber" | "rose";
  onClick: () => void;
}) {
  const toneClass =
    tone === "emerald"
      ? "border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/10"
      : tone === "amber"
        ? "border-amber-500/40 text-amber-400 hover:bg-amber-500/10"
        : "border-rose-500/40 text-rose-400 hover:bg-rose-500/10";

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn("border px-3 py-1.5 text-[10px] font-medium transition-colors", toneClass)}
    >
      {label}
    </button>
  );
}

function ArchiveTab({
  briefing,
  history,
  loading,
}: {
  briefing: ReturnType<typeof useContextBriefing>["briefing"];
  history: PipelineHistoryEntry[];
  loading: boolean;
}) {
  const { t } = useTranslations("ui");
  const apiDecisions = briefing?.recent_decisions ?? [];
  const pipelineRecords = dedupeHistoryByAssetDate(history).filter((h) => h.ai_insight || h.action_plan);

  return (
    <div className="space-y-4">
      <header className="border border-[#27272A] bg-[#18181B] px-4 py-3">
        <p className="text-[10px] uppercase tracking-wider text-zinc-500">{t("ai.archiveTitle")}</p>
        <p className="mt-1 text-[13px] text-zinc-200">{t("ai.archiveSubtitle")}</p>
      </header>

      <StructuredBriefingCards structured={briefing?.structured} loading={loading} />

      {briefing?.mode === "technical" ? (
        <TechnicalBriefingCards technical={briefing.technical} loading={loading} />
      ) : null}

      {briefing?.technical_detail ? (
        <AiSectionCard title={t("ai.technicalDetail")} accent="blue">
          <p className="whitespace-pre-wrap text-[12px] leading-relaxed text-zinc-300">{briefing.technical_detail}</p>
        </AiSectionCard>
      ) : null}

      {briefing?.recommendation_quality ? (
        <OpsPanel title={t("ai.recommendationQualityMetrics")} meta={t("ai.proxyMetricsMeta")} density="comfortable">
          <div className="grid gap-2 sm:grid-cols-4">
            <MetricChip
              label={t("ai.qualityScore")}
              value={`${briefing.recommendation_quality.quality_score?.toFixed(0) ?? "0"}`}
            />
            <MetricChip
              label={t("ai.recommendationCoverage")}
              value={`%${(briefing.recommendation_quality.action_coverage * 100).toFixed(0)}`}
            />
            <MetricChip
              label={t("ai.postActionImprovement")}
              value={`%${(briefing.recommendation_quality.improved_after_action_ratio * 100).toFixed(0)}`}
            />
            <MetricChip
              label={t("ai.sampleSize")}
              value={`${briefing.recommendation_quality.samples}`}
            />
          </div>
        </OpsPanel>
      ) : null}

      {apiDecisions.length > 0 ? (
        <OpsPanel title={t("ai.recentAiDecisions")} meta={t("ai.briefingApiMeta")} density="comfortable">
          <div className="grid gap-2 md:grid-cols-2">
            {apiDecisions.map((d, i) => (
              <AiSectionCard key={i} title={formatHistoryTime(d.at)} accent="blue">
                <p className="text-[11px] leading-relaxed text-zinc-300">{d.insight}</p>
                {d.action ? <p className="mt-2 font-mono text-[10px] text-[#3B82F6]">→ {d.action}</p> : null}
              </AiSectionCard>
            ))}
          </div>
        </OpsPanel>
      ) : null}

      <OpsPanel title={t("ai.pipelineDecisionHistory")} meta={t("commonUi.recordsMeta", { count: pipelineRecords.length })} density="comfortable">
        <div className="space-y-0">
          {pipelineRecords.slice(0, 20).map((entry, i) => (
            <div key={i} className="grid gap-2 border-b border-[#27272A] py-3 last:border-0 lg:grid-cols-[140px_1fr]">
              <div>
                <p className="font-mono text-[10px] text-zinc-500">{entry.target_date}</p>
                <p className="text-[10px] text-zinc-600">{entry.asset_id}</p>
              </div>
              <div>
                <p className="text-[11px] leading-relaxed text-zinc-300">{entry.ai_insight}</p>
                {entry.action_plan ? (
                  <p className="mt-2 font-mono text-[10px] text-[#3B82F6]">→ {entry.action_plan}</p>
                ) : null}
              </div>
            </div>
          ))}
          {!loading && pipelineRecords.length === 0 ? (
            <p className="py-4 text-[10px] text-zinc-600">{t("ai.noHistoryRunPipeline")}</p>
          ) : null}
        </div>
      </OpsPanel>
    </div>
  );
}

function statusLabel(status: string, t: (key: string) => string): string {
  if (status === "approved") return t("ai.approved");
  if (status === "postponed") return t("ai.postponed");
  if (status === "rejected") return t("ai.rejected");
  return status;
}

function formatHistoryTime(at: string): string {
  try {
    const d = new Date(at);
    if (!Number.isNaN(d.getTime())) {
      return d.toLocaleString("tr-TR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
    }
  } catch {
    // yedek
  }
  return at.slice(0, 16);
}

function MetricChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-[#27272A] bg-[#18181B] p-2.5">
      <p className="text-[9px] uppercase tracking-[0.08em] text-zinc-600">{label}</p>
      <p className="mt-1 font-mono text-[13px] text-zinc-200">{value}</p>
    </div>
  );
}
