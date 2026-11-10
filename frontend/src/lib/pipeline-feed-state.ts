export type PipelineFeedState = "ready" | "running" | "synced" | "lag" | "offline";

export const PIPELINE_FEED_LABELS: Record<PipelineFeedState, string> = {
  ready: "Hazır",
  running: "Çalışıyor",
  synced: "Senkronize",
  lag: "Gecikme",
  offline: "Offline",
};

export const PIPELINE_FEED_STYLES: Record<
  PipelineFeedState,
  { text: string; dot: string; pulse?: boolean }
> = {
  ready: { text: "text-zinc-500", dot: "bg-zinc-500" },
  running: { text: "text-emerald-400", dot: "bg-emerald-400", pulse: true },
  synced: { text: "text-blue-400", dot: "bg-blue-400" },
  lag: { text: "text-amber-400", dot: "bg-amber-400" },
  offline: { text: "text-rose-400", dot: "bg-rose-400" },
};

/** @deprecated Tek kaynak: `@/lib/live-refresh` */
export { PIPELINE_LAG_THRESHOLD_MS } from "@/lib/live-refresh";
