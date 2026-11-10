"use client";

import { useTranslations } from "@/context/locale-context";
import type { ContextBriefingStructured, ContextBriefingTechnical } from "@/lib/api";
import { cn } from "@/lib/utils";

export function AiSectionCard({
  title,
  children,
  accent = "blue",
  className,
}: {
  title: string;
  children: React.ReactNode;
  accent?: "blue" | "amber" | "emerald" | "rose" | "zinc";
  className?: string;
}) {
  const border = {
    blue: "border-l-[#3B82F6]",
    amber: "border-l-amber-500",
    emerald: "border-l-[#3B82F6]",
    rose: "border-l-rose-500",
    zinc: "border-l-zinc-600",
  }[accent];

  return (
    <section className={cn("border border-[#27272A] border-l-2 bg-[#18181B] p-4", border, className)}>
      <h3 className="text-[10px] font-semibold uppercase tracking-[0.12em] text-zinc-500">{title}</h3>
      <div className="mt-2.5">{children}</div>
    </section>
  );
}

export function AiFieldCard({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="border border-[#27272A] bg-[#141416] p-3">
      <p className="text-[9px] font-semibold uppercase tracking-[0.08em] text-zinc-600">{label}</p>
      <p className={cn("mt-1.5 text-[12px] leading-relaxed text-zinc-200", mono && "font-mono text-[11px]")}>
        {value}
      </p>
    </div>
  );
}

export function StructuredBriefingCards({
  structured,
  loading,
}: {
  structured?: ContextBriefingStructured | null;
  loading?: boolean;
}) {
  const { t } = useTranslations("ui");

  if (loading) {
    return (
      <AiSectionCard title={t("ai.structuredAnalysis")}>
        <p className="text-[11px] text-zinc-500">{t("ai.analysisPreparing")}</p>
      </AiSectionCard>
    );
  }
  if (!structured) {
    return (
      <AiSectionCard title={t("ai.structuredAnalysis")}>
        <p className="text-[11px] text-zinc-500">{t("ai.structuredWhenPipeline")}</p>
      </AiSectionCard>
    );
  }

  const fields: Array<{ label: string; value: string; mono?: boolean; accent?: "blue" | "amber" | "emerald" | "rose" | "zinc" }> = [
    { label: t("ai.title"), value: structured.title },
    { label: t("ai.statusSummary"), value: structured.status_summary },
    { label: t("ai.analysis"), value: structured.analysis },
    { label: t("risk.risk"), value: structured.risk, accent: "amber" },
    { label: t("ai.financialImpact"), value: structured.financial_impact, accent: "rose" },
    { label: t("ai.operationalImpact"), value: structured.operational_impact },
    { label: t("ai.recommendedAction"), value: structured.recommended_action, mono: true, accent: "emerald" },
    { label: t("ai.alternativeAction"), value: structured.alternative_action, mono: true, accent: "zinc" },
  ];

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2 border border-[#27272A] bg-[#0C0E14] px-4 py-3">
        <p className="text-[13px] font-medium text-zinc-100">{structured.title}</p>
        <ConfidencePill value={structured.confidence} />
      </div>
      <div className="grid gap-2 lg:grid-cols-2">
        {fields.slice(1).map((f) => (
          <AiSectionCard key={f.label} title={f.label} accent={f.accent ?? "blue"}>
            <p className={cn("text-[12px] leading-relaxed text-zinc-300", f.mono && "font-mono text-[11px] text-[#93C5FD]")}>
              {f.value}
            </p>
          </AiSectionCard>
        ))}
      </div>
    </div>
  );
}

export function TechnicalBriefingCards({
  technical,
  loading,
}: {
  technical?: ContextBriefingTechnical | null;
  loading?: boolean;
}) {
  const { t } = useTranslations("ui");
  if (loading || !technical) return null;

  return (
    <div className="space-y-3">
      <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#3B82F6]">{t("ai.technicalMode")}</p>
      <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-4">
        <AiFieldCard label={t("ai.model")} value={technical.model} mono />
        <AiFieldCard label={t("ai.confidence")} value={`%${technical.confidence}`} mono />
        <AiFieldCard label={t("ai.forecastQuality")} value={technical.forecast_quality} />
        <AiFieldCard label={t("ai.dataQuality")} value={technical.data_quality} />
      </div>
      {technical.feature_importance?.length ? (
        <AiSectionCard title={t("ai.featureImportance")} accent="blue">
          <ul className="space-y-2">
            {technical.feature_importance.map((f) => (
              <li key={f.feature} className="flex items-center gap-3 py-1">
                <span className="w-36 shrink-0 truncate text-[11px] text-zinc-400">{f.feature}</span>
                <div className="h-1.5 flex-1 bg-[#27272A]">
                  <div
                    className="h-full bg-[#3B82F6]"
                    style={{ width: `${Math.round(f.weight * 100)}%` }}
                  />
                </div>
                <span className="w-10 shrink-0 text-right font-mono text-[10px] text-zinc-500">
                  {(f.weight * 100).toFixed(0)}%
                </span>
              </li>
            ))}
          </ul>
        </AiSectionCard>
      ) : null}
    </div>
  );
}

export function ConfidencePill({ value }: { value: number }) {
  const { t } = useTranslations("ui");
  // Yüksek güven nötr; yalnızca düşük güven uyarır
  const tone =
    value >= 65
      ? "border-[#27272A] text-zinc-300"
      : value >= 45
        ? "border-amber-500/40 text-amber-400"
        : "border-rose-500/40 text-rose-400";
  return (
    <span className={cn("border px-2.5 py-1 font-mono text-[11px] tabular-nums", tone)}>
      {t("ai.confidencePct", { value: value.toFixed(0) })}
    </span>
  );
}

export function RecommendationCards({ items, loading }: { items: string[]; loading?: boolean }) {
  const { t } = useTranslations("ui");
  return (
    <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
      {items.map((item, i) => (
        <AiSectionCard key={i} title={t("ai.recommendationN", { n: i + 1 })} accent={i === 0 ? "blue" : "zinc"}>
          <p className="text-[12px] leading-relaxed text-zinc-300">{loading ? "—" : item}</p>
        </AiSectionCard>
      ))}
      {!loading && items.length === 0 ? (
        <AiSectionCard title={t("ai.recommendation")}>
          <p className="text-[11px] text-zinc-600">{t("ai.noRecommendationYet")}</p>
        </AiSectionCard>
      ) : null}
    </div>
  );
}
