"use client";

import { createContext, useContext, useMemo, type ReactNode } from "react";

import { useContextBriefing } from "@/hooks/use-context-briefing";
import type { BriefingAnnotation, ContextBriefingResponse } from "@/lib/api";
import { findAlertAnnotation, findKpiAnnotation, getAllAnnotations } from "@/lib/annotations";

interface AnnotationsContextValue {
  briefing: ContextBriefingResponse | null;
  annotations: BriefingAnnotation[];
  loading: boolean;
  getKpi: (kpiId: string) => BriefingAnnotation | undefined;
  getAlert: (ruleId: string) => BriefingAnnotation | undefined;
}

const AnnotationsContext = createContext<AnnotationsContextValue | null>(null);

export function AnnotationsProvider({
  context,
  days = 7,
  children,
}: {
  context: string;
  days?: number;
  children: ReactNode;
}) {
  const { briefing, loading } = useContextBriefing(context, days);
  const annotations = useMemo(() => getAllAnnotations(briefing), [briefing]);

  const value = useMemo<AnnotationsContextValue>(
    () => ({
      briefing,
      annotations,
      loading,
      getKpi: (kpiId) => findKpiAnnotation(annotations, kpiId),
      getAlert: (ruleId) => findAlertAnnotation(annotations, ruleId),
    }),
    [briefing, annotations, loading],
  );

  return <AnnotationsContext.Provider value={value}>{children}</AnnotationsContext.Provider>;
}

export function useAnnotations(): AnnotationsContextValue {
  const ctx = useContext(AnnotationsContext);
  if (!ctx) {
    return {
      briefing: null,
      annotations: [],
      loading: false,
      getKpi: () => undefined,
      getAlert: () => undefined,
    };
  }
  return ctx;
}
