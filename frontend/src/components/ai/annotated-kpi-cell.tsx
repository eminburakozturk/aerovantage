"use client";

import type { ComponentProps } from "react";

import { AiInlineHint } from "@/components/ai/ai-inline-hint";
import { useAnnotations } from "@/components/ai/annotations-context";
import { KpiCell } from "@/components/ops/kpi-cell";
import { emphasisBorderClass, levelToKpiStatus, resolveKpiBorderLevel } from "@/lib/status-level";
import { cn } from "@/lib/utils";

type AnnotatedKpiCellProps = ComponentProps<typeof KpiCell> & {
  kpiId: string;
};

export function AnnotatedKpiCell({
  kpiId,
  className,
  emphasis,
  status = "neutral",
  ...props
}: AnnotatedKpiCellProps) {
  const { getKpi, loading } = useAnnotations();
  const annotation = getKpi(kpiId);
  // Border = AI severity (ipucu ile eş); annotation yoksa metrik status
  const borderLevel = resolveKpiBorderLevel(annotation?.severity, status);
  const effectiveStatus = levelToKpiStatus(borderLevel);

  return (
    <div className={cn("flex min-w-0 flex-col", emphasisBorderClass(borderLevel), className)}>
      <KpiCell {...props} status={effectiveStatus} emphasis={emphasis} className="border-r-0" />
      <AiInlineHint annotation={annotation} loading={loading} compact className="px-3 pb-2" />
    </div>
  );
}
