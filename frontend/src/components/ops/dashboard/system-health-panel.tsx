"use client";

import { OpsPanel } from "@/components/ops/ops-panel";
import { StatusIndicator } from "@/components/ops/status-indicator";
import { useTranslations } from "@/context/locale-context";
import type { HealthResponse } from "@/lib/api";
import { cn } from "@/lib/utils";

interface SystemHealthPanelProps {
  health: HealthResponse | null;
  loading?: boolean;
  className?: string;
}

export function SystemHealthPanel({ health, loading, className }: SystemHealthPanelProps) {
  const { t } = useTranslations("monitoring");
  const hubs = health ? Object.entries(health.data_hub) : [];
  const hasNonLiveHub = hubs.some(
    ([, hub]) =>
      hub.mode === "mock" ||
      hub.mode === "simulated" ||
      hub.mode === "fallback" ||
      hub.status !== "ok",
  );
  const allOk = health?.status === "ok" && !hasNonLiveHub;
  const status = loading ? "idle" : allOk ? "ok" : health ? "warn" : "crit";

  const modeLabel = (name: string, mode?: string) => {
    if (mode === "simulated" || name === "scada") {
      if (mode === "simulated" || mode === "mock") return t("hub.simulated");
    }
    if (mode === "live") return t("hub.live");
    if (mode === "mock") return t("hub.mock");
    if (mode === "fallback") return t("hub.fallback");
    return mode ?? "";
  };

  return (
    <OpsPanel
      title={t("healthTitle")}
      meta={t("healthMeta")}
      density="comfortable"
      className={cn("flex h-full min-h-0 flex-col overflow-hidden", className)}
    >
      <div className="flex h-full min-h-0 flex-col gap-2 overflow-hidden">
        <StatusIndicator
          status={status}
          label={
            loading
              ? t("checking")
              : allOk
                ? t("allLive")
                : hasNonLiveHub
                  ? t("mockMode")
                  : t("degraded")
          }
        />
        {health ? (
          <div className="grid min-h-0 flex-1 grid-cols-2 gap-1.5 overflow-hidden sm:grid-cols-4">
            {hubs.map(([name, hub]) => {
              const nonLive =
                hub.mode === "mock" ||
                hub.mode === "simulated" ||
                hub.mode === "fallback" ||
                hub.status !== "ok";
              return (
                <div
                  key={name}
                  className="flex min-h-0 flex-col justify-between gap-1 overflow-hidden border border-[#27272A] bg-[#141416] px-2 py-1.5"
                >
                  <div className="min-w-0">
                    <span className="block truncate text-[10px] font-medium uppercase tracking-wide text-zinc-300">
                      {name}
                    </span>
                    <span className="mt-0.5 line-clamp-2 text-[8px] leading-tight text-zinc-600">
                      {modeLabel(name, hub.mode)}
                    </span>
                  </div>
                  <span
                    className={cn(
                      "shrink-0 font-mono text-[9px] font-semibold uppercase",
                      nonLive ? "text-amber-400" : "text-zinc-400",
                    )}
                  >
                    {nonLive ? hub.mode || hub.status : t("hub.ok")}
                  </span>
                </div>
              );
            })}
          </div>
        ) : loading ? (
          <p className="text-[11px] text-zinc-600">{t("checking")}</p>
        ) : (
          <p className="text-[11px] text-zinc-600">{t("backendWaiting")}</p>
        )}
      </div>
    </OpsPanel>
  );
}
