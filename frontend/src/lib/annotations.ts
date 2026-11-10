import type { BriefingAnnotation, ContextBriefingResponse } from "@/lib/api";

export function getAllAnnotations(briefing: ContextBriefingResponse | null): BriefingAnnotation[] {
  if (!briefing) return [];
  return briefing.annotations ?? [];
}

export function findAnnotation(
  annotations: BriefingAnnotation[],
  targetType: string,
  targetId: string,
): BriefingAnnotation | undefined {
  return annotations.find((a) => a.target_type === targetType && a.target_id === targetId);
}

export function findKpiAnnotation(
  annotations: BriefingAnnotation[],
  kpiId: string,
): BriefingAnnotation | undefined {
  return findAnnotation(annotations, "kpi", kpiId);
}

export function findAlertAnnotation(
  annotations: BriefingAnnotation[],
  ruleId: string,
): BriefingAnnotation | undefined {
  return findAnnotation(annotations, "alert", ruleId);
}

export function extractActionableAnnotations(briefing: ContextBriefingResponse | null): BriefingAnnotation[] {
  if (!briefing) return [];

  if (briefing.annotations?.length) {
    return briefing.annotations.filter((a) => Boolean(a.recommended_action?.trim()));
  }

  const fallback: BriefingAnnotation[] = [];
  const structured = briefing.structured;
  const context = briefing.context ?? "ai";

  if (structured?.recommended_action) {
    fallback.push({
      id: `decision-primary-${context}`,
      target_type: "decision",
      target_id: "primary",
      label: structured.title ?? "Recommended action",
      insight: structured.status_summary ?? "",
      severity: briefing.metrics.risk_score > 75 ? "crit" : briefing.metrics.risk_score > 50 ? "warn" : "normal",
      confidence: structured.confidence ?? briefing.metrics.confidence ?? 0,
      recommended_action: structured.recommended_action,
      context,
    });
  }

  if (structured?.alternative_action) {
    fallback.push({
      id: `decision-alt-${context}`,
      target_type: "decision",
      target_id: "alternative",
      label: "Alternative action",
      insight: structured.operational_impact ?? "",
      severity: "normal",
      confidence: Math.max(0, (structured.confidence ?? 0) - 10),
      recommended_action: structured.alternative_action,
      context,
    });
  }

  briefing.recommendations?.forEach((rec, i) => {
    if (!rec?.trim()) return;
    if (rec === structured?.recommended_action || rec === structured?.alternative_action) return;
    fallback.push({
      id: `rec-${context}-${i}`,
      target_type: "recommendation",
      target_id: `rec-${i}`,
      label: "AI recommendation",
      insight: rec,
      severity: "normal",
      confidence: structured?.confidence ?? 0,
      recommended_action: rec,
      context,
    });
  });

  return fallback;
}
