/** Pipeline history helpers — (asset_id, target_date) başına en yeni kayıt. */

export function dedupeHistoryByAssetDate<T extends { asset_id?: string; target_date?: string; saved_at?: string }>(
  history: T[],
): T[] {
  const seen = new Set<string>();
  const out: T[] = [];
  for (const entry of history) {
    const day = (entry.target_date || entry.saved_at?.slice(0, 10) || "").trim();
    const key = `${entry.asset_id ?? ""}|${day}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(entry);
  }
  return out;
}

/** Tarihe göre artan sıralı trend satırları (benzersiz gün). `costKey` tooltip/seri adı (i18n). */
export function historyTrendRows<
  T extends {
    target_date?: string;
    total_imbalance_cost_tl?: number | null;
    risk_score?: number | null;
    mape_percentage?: number | null;
  },
>(
  history: T[],
  limit = 12,
  costKey = "Cost",
): Array<{ tarih: string; Risk: number; MAPE: number } & Record<string, string | number>> {
  const unique = dedupeHistoryByAssetDate(history)
    .filter((h) => h.target_date)
    .slice(0, limit);
  return [...unique]
    .sort((a, b) => String(a.target_date).localeCompare(String(b.target_date)))
    .map((h) => ({
      tarih: h.target_date ?? "—",
      [costKey]: h.total_imbalance_cost_tl ?? 0,
      Risk: h.risk_score ?? 0,
      MAPE: h.mape_percentage ?? 0,
    }));
}
