"use client";

import Link from "next/link";

import { useTranslations } from "@/context/locale-context";
import type { BriefingAnnotation } from "@/lib/api";
import { cn } from "@/lib/utils";
import { isAlertLevel, normalizeSeverity, STATUS_COLORS } from "@/lib/status-level";

interface AiInlineHintProps {
  annotation?: BriefingAnnotation | null;
  loading?: boolean;
  className?: string;
  compact?: boolean;
}

export function AiInlineHint({ annotation, loading, className, compact = false }: AiInlineHintProps) {
  const { t } = useTranslations("ui");

  if (loading) {
    return <p className={cn("text-[8px] text-zinc-700", className)}>{t("ai.hintLoading")}</p>;
  }

  if (!annotation?.insight?.trim()) return null;

  const severity = normalizeSeverity(annotation.severity);
  const colors = STATUS_COLORS[severity];
  const alert = isAlertLevel(severity);

  return (
    <div
      className={cn(
        "border-t border-[#27272A]/80 pt-1.5",
        compact ? "mt-1" : "mt-2",
        className,
      )}
      title={annotation.recommended_action || undefined}
    >
      <div className="flex items-start gap-1.5">
        <span className={cn("mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full", colors.dot)} aria-hidden />
        <p className={cn("min-w-0 flex-1 leading-snug text-zinc-500 line-clamp-2", compact ? "text-[8px]" : "text-[9px]")}>
          <span className={cn("font-medium", alert ? colors.text : "text-zinc-400")}>{t("ai.aiPrefix")}</span>
          <span className="text-zinc-500">{annotation.insight}</span>
        </p>
      </div>
      {annotation.recommended_action ? (
        <Link
          href={`/ai?from=${encodeURIComponent(annotation.context)}`}
          className={cn(
            "mt-0.5 block break-words font-mono leading-snug text-[#3B82F6] hover:underline",
            compact ? "text-[8px]" : "text-[9px]",
          )}
        >
          → {annotation.recommended_action}
        </Link>
      ) : null}
    </div>
  );
}
