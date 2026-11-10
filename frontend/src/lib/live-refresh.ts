/** EPİAŞ veri tanesi saatliktir (PTF / realtime-generation HH:00). */

/** Tam pipeline (EPİAŞ + SCADA simulator + Gemini) — saatlik taneye hizalı */
export const AUTO_PIPELINE_INTERVAL_MS = 60 * 60 * 1000;

/**
 * Hafif UI yenileme (son history + health).
 * EPİAŞ yeni saat dilimi yayınlamadan önce bile connector durumunu taze tutar.
 */
export const AUTO_DASHBOARD_REFRESH_MS = 10 * 60 * 1000;

/** Lag: otomatik pipeline aralığının biraz üzeri */
export const PIPELINE_LAG_THRESHOLD_MS = 70 * 60 * 1000;
