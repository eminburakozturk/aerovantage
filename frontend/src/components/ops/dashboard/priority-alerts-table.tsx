"use client";

import { OpsPanel } from "@/components/ops/ops-panel";
import { useAlertAcks } from "@/hooks/use-alert-acks";
import { useOperasyon } from "@/context/operasyon-context";
import { useTranslations } from "@/context/locale-context";
import type { DashboardData } from "@/lib/api";
import { localizeRule } from "@/lib/localize-rules";
import { cn } from "@/lib/utils";
import { normalizeSeverity, STATUS_COLORS } from "@/lib/status-level";

interface PriorityAlertsTableProps {
  data: DashboardData | null;
  className?: string;
}

interface AlertRow {
  id: string;
  type: "rule" | "notification";
  severity: string;
  message: string;
  action?: string;
}

export function PriorityAlertsTable({ data, className }: PriorityAlertsTableProps) {
  const { ack, isAcked } = useAlertAcks();
  const { t } = useTranslations("ui");
  const { scadaIsMock } = useOperasyon();

  const rows: AlertRow[] = [
    ...(data?.rules ?? []).map((rule) => {
      const localized = localizeRule(t, rule, scadaIsMock);
      return {
        id: `rule-${rule.rule_id}`,
        type: "rule" as const,
        severity: rule.severity,
        message: localized.message,
        action: localized.action,
      };
    }),
    ...(data?.notifications ?? []).map((n, i) => ({
      id: `notif-${n.title}-${i}`,
      type: "notification" as const,
      severity: n.level ?? "info",
      message: `${n.title}: ${n.message}`,
    })),
  ];

  const activeRows = rows.filter((r) => !isAcked(r.id));
  const ackedCount = rows.length - activeRows.length;

  return (
    <OpsPanel
      title={t("ops.priorityAlerts")}
      meta={t("ops.alertsSummary", {
        active: activeRows.length,
        acked: ackedCount,
        critical: data?.criticalAlertsCount ?? 0,
      })}
      density="comfortable"
      className={cn("flex h-full min-h-0 flex-col", className)}
    >
      {activeRows.length === 0 ? (
        <div className="flex flex-1 items-center px-2">
          <p className="text-[11px] text-zinc-400">
            {rows.length > 0 ? t("ops.allAlertsAcked") : t("ops.noActiveAlertsNormal")}
          </p>
        </div>
      ) : (
        <div className="min-h-0 flex-1 overflow-auto">
          <table className="w-full text-left text-[10px]">
            <thead className="sticky top-0 bg-[#18181B] text-[9px] uppercase tracking-wider text-zinc-600">
              <tr className="border-b border-[#27272A]">
                <th className="px-2 py-1.5 font-medium">{t("ops.status")}</th>
                <th className="px-2 py-1.5 font-medium">{t("ops.type")}</th>
                <th className="px-2 py-1.5 font-medium">{t("ops.message")}</th>
                <th className="px-2 py-1.5 font-medium text-right">{t("ops.action")}</th>
              </tr>
            </thead>
            <tbody>
              {activeRows.map((row) => {
                const level = normalizeSeverity(row.severity);
                const colors = STATUS_COLORS[level];
                return (
                  <tr key={row.id} className="border-b border-[#27272A] last:border-0">
                    <td className="px-2 py-2">
                      <span className={cn("font-semibold uppercase", colors.text)}>{t(`status.${level}`)}</span>
                    </td>
                    <td className="px-2 py-2 text-zinc-500">
                      {row.type === "rule" ? t("ops.rule") : t("ops.notification")}
                    </td>
                    <td className="px-2 py-2">
                      <p className="text-[11px] leading-snug text-zinc-200">{row.message}</p>
                      {row.action ? <p className="mt-0.5 text-[9px] text-zinc-600">→ {row.action}</p> : null}
                    </td>
                    <td className="px-2 py-2 text-right">
                      <button
                        type="button"
                        onClick={() => ack(row.id)}
                        className="border border-emerald-500/40 px-2 py-1 text-[9px] font-medium text-emerald-400 transition-colors hover:bg-emerald-500/10"
                      >
                        {t("ops.approve")}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </OpsPanel>
  );
}
