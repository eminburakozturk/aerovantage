/** Büyük TL tutarlarını KPI hücresine sığacak şekilde formatlar. */
export function formatCurrencyCompact(value: number): { display: string; full: string } {
  const full = `${value.toLocaleString("tr-TR", { maximumFractionDigits: 2 })} TL`;
  if (Math.abs(value) >= 1_000_000) {
    return { display: `${(value / 1_000_000).toFixed(2)}M`, full };
  }
  if (Math.abs(value) >= 100_000) {
    return { display: `${(value / 1_000).toFixed(0)}K`, full };
  }
  return { display: value.toLocaleString("tr-TR", { maximumFractionDigits: 0 }), full };
}

export function formatMape(value: number | undefined | null): string {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  return Math.min(999, Math.max(0, value)).toFixed(1);
}

export function formatCurrencyTl(value: number | undefined | null): string {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  return `${value.toLocaleString("tr-TR")} TL`;
}

export function formatTimeShort(value: Date | string): string {
  const date = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
}

export function formatDateTime(value: Date | string): string {
  const date = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("tr-TR");
}
