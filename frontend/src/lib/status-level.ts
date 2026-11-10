export type StatusLevel = "normal" | "warn" | "crit" | "info" | "unknown";

/** Sabit TR etiketler — UI'da useTranslations("common").statusLabel tercih et */
export const STATUS_LABELS: Record<StatusLevel, string> = {
  normal: "Normal",
  warn: "Uyarı",
  crit: "Kritik",
  info: "Bilgi",
  unknown: "Bilinmiyor",
};

export const STATUS_COLORS: Record<StatusLevel, { text: string; border: string; bg: string; dot: string }> = {
  // normal = nötr (yeşil "her şey iyi" sinyali vermesin)
  normal: { text: "text-zinc-100", border: "border-[#27272A]", bg: "bg-[#18181B]", dot: "bg-zinc-500" },
  warn: { text: "text-amber-400", border: "border-amber-500/40", bg: "bg-amber-500/10", dot: "bg-amber-400" },
  crit: { text: "text-rose-400", border: "border-rose-500/40", bg: "bg-rose-500/10", dot: "bg-rose-500" },
  info: { text: "text-blue-400", border: "border-blue-500/40", bg: "bg-blue-500/10", dot: "bg-blue-500" },
  unknown: { text: "text-zinc-400", border: "border-[#27272A]", bg: "bg-[#18181B]", dot: "bg-zinc-600" },
};

export function normalizeSeverity(value?: string | null): StatusLevel {
  const v = (value ?? "").toLowerCase();
  if (["crit", "critical", "kritik", "high", "yüksek"].includes(v)) return "crit";
  if (["warn", "warning", "medium", "orta"].includes(v)) return "warn";
  if (["info", "bilgi", "information", "low"].includes(v)) return "info";
  if (["normal", "ok", "düşük", "green"].includes(v)) return "normal";
  return "unknown";
}

export function severityFromRisk(risk?: number | null): StatusLevel {
  if (risk == null) return "unknown";
  if (risk > 75) return "crit";
  if (risk > 50) return "warn";
  return "normal";
}

export function operationalStatusFromRisk(risk?: number | null): "ok" | "warn" | "crit" {
  const level = severityFromRisk(risk);
  if (level === "crit") return "crit";
  if (level === "warn") return "warn";
  return "ok";
}

export function kpiStatusToLevel(status: "ok" | "warn" | "crit" | "info" | "neutral"): StatusLevel {
  if (status === "ok") return "normal";
  if (status === "neutral") return "unknown";
  return status;
}

/**
 * KPI çerçeve rengi — AI annotation severity öncelikli (aynı AI satırı → aynı border).
 * Annotation yoksa / bilinmiyorsa metrik status'una düşer.
 * AI "normal" ise nötr çerçeve (metrik crit olsa bile).
 */
export function resolveKpiBorderLevel(
  aiSeverity: string | null | undefined,
  status: "ok" | "warn" | "crit" | "info" | "neutral" = "neutral",
): StatusLevel {
  if (aiSeverity != null && String(aiSeverity).trim() !== "") {
    const fromAi = normalizeSeverity(aiSeverity);
    if (fromAi !== "unknown") return fromAi;
  }
  return kpiStatusToLevel(status);
}

export function levelToKpiStatus(level: StatusLevel): "ok" | "warn" | "crit" | "info" | "neutral" {
  if (level === "crit") return "crit";
  if (level === "warn") return "warn";
  if (level === "info") return "info";
  // normal/unknown → nötr metin (yeşil "ok" yok)
  return "neutral";
}

/** Uyarı/kritikte sol vurgu; aksi halde nötr çerçeve */
export function emphasisBorderClass(level: StatusLevel): string {
  if (level === "warn" || level === "crit") {
    const solid = STATUS_COLORS[level].border.replace("/40", "");
    return `border border-l-2 bg-[#18181B] ${solid}`;
  }
  return "border border-[#27272A] bg-[#18181B]";
}

/** true yalnızca gerçek uyarı/kritik için */
export function isAlertLevel(level: StatusLevel): boolean {
  return level === "warn" || level === "crit";
}
