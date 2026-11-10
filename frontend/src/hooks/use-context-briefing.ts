"use client";

import { useEffect, useState } from "react";

import { fetchContextBriefing, type ContextBriefingResponse } from "@/lib/api";
import { useOperasyon } from "@/context/operasyon-context";
import { useLocale } from "@/context/locale-context";

export function useContextBriefing(context: string | undefined, days = 7) {
  const { selectedAssetId } = useOperasyon();
  const { locale } = useLocale();
  const [briefing, setBriefing] = useState<ContextBriefingResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!context || !selectedAssetId) {
      setBriefing(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    void fetchContextBriefing(context, selectedAssetId, days, locale)
      .then((data) => {
        if (!cancelled) setBriefing(data);
      })
      .catch(() => {
        if (!cancelled) setBriefing(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [context, selectedAssetId, days, locale]);

  return { briefing, loading };
}
