import { cn } from "@/lib/utils";
import { formatCurrencyCompact } from "@/lib/format";

type KpiStatus = "ok" | "warn" | "crit" | "info" | "neutral";

interface KpiCellProps {
  label: string;
  value: string;
  unit?: string;
  sub?: string;
  delta?: string;
  deltaPositive?: boolean;
  updatedAt?: string;
  status?: KpiStatus;
  title?: string;
  compactCurrency?: number;
  trend?: number[];
  /** Operatör odaklı KPI — daha büyük ve vurgulu */
  emphasis?: boolean;
  /** Panel alanı dar olduğunda daha düşük KPI yüksekliği */
  compact?: boolean;
  className?: string;
}

const STATUS_COLOR: Record<KpiStatus, string> = {
  ok: "text-zinc-100",
  warn: "text-amber-400",
  crit: "text-rose-400",
  info: "text-blue-400",
  neutral: "text-zinc-100",
};

const TREND_STROKE: Record<KpiStatus, string> = {
  ok: "#a1a1aa",
  warn: "#f59e0b",
  crit: "#f43f5e",
  info: "#60a5fa",
  neutral: "#71717a",
};

function KpiSparkline({ values, status }: { values: number[]; status: KpiStatus }) {
  const clean = values.filter((v) => Number.isFinite(v));
  if (clean.length < 2) return null;

  const min = Math.min(...clean);
  const max = Math.max(...clean);
  const range = max - min || 1;
  const w = 56;
  const h = 20;
  const points = clean
    .map((v, i) => {
      const x = (i / (clean.length - 1)) * w;
      const y = h - ((v - min) / range) * (h - 2) + 1;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      className="mt-2 h-5 w-14 shrink-0 opacity-80"
      aria-hidden
    >
      <polyline
        fill="none"
        stroke={TREND_STROKE[status]}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
    </svg>
  );
}

export function KpiCell({
  label,
  value,
  unit,
  sub,
  delta,
  deltaPositive,
  updatedAt,
  status = "neutral",
  title,
  compactCurrency,
  trend,
  emphasis = false,
  compact = false,
  className,
}: KpiCellProps) {
  const currency =
    compactCurrency !== undefined ? formatCurrencyCompact(compactCurrency) : null;
  const displayValue = currency ? currency.display : value;
  const tooltip = title ?? currency?.full;

  return (
    <div
      className={cn(
        "flex min-w-0 flex-col justify-between overflow-hidden border-r border-[#27272A] transition-colors duration-200 last:border-r-0",
        compact
          ? emphasis
            ? "px-3 py-3.5 hover:bg-[#1c1c1f]/40"
            : "px-3 py-2 hover:bg-[#1c1c1f]"
          : emphasis
            ? "px-3 py-4 hover:bg-[#1c1c1f]/40"
            : "px-3 py-2.5 hover:bg-[#1c1c1f]",
        className,
      )}
      title={tooltip}
    >
      <div className="min-w-0">
        <span
          className={cn(
            "truncate font-semibold uppercase tracking-[0.1em]",
            emphasis ? "text-[10px] text-zinc-400" : "text-[9px] text-zinc-500",
          )}
        >
          {label}
        </span>
        <div
          className={cn(
            "flex min-w-0 items-end justify-between gap-2",
            compact ? (emphasis ? "mt-1.5" : "mt-1") : emphasis ? "mt-2" : "mt-1.5",
          )}
        >
          <div className="min-w-0">
            <div className="flex min-w-0 items-baseline gap-1">
              <span
                className={cn(
                  "truncate font-mono font-semibold tabular-nums leading-none",
                  compact ? (emphasis ? "text-[1.65rem]" : "text-[1.1rem] font-medium") : emphasis ? "text-3xl" : "text-xl font-medium",
                  STATUS_COLOR[status],
                )}
              >
                {displayValue}
              </span>
              {unit ? (
                <span className="shrink-0 font-mono text-[10px] text-zinc-600">{unit}</span>
              ) : null}
            </div>
            {delta ? (
              <span
                className={cn(
                  "mt-1 block truncate font-mono text-[10px]",
                  deltaPositive === true
                    ? "text-zinc-400"
                    : deltaPositive === false
                      ? "text-rose-400"
                      : "text-zinc-500",
                )}
              >
                {delta}
              </span>
            ) : null}
          </div>
          {trend && trend.length > 1 ? <KpiSparkline values={trend} status={status} /> : null}
        </div>
      </div>
      <div className="mt-2 min-w-0">
        {sub ? <span className="block truncate text-[9px] text-zinc-600">{sub}</span> : null}
        {updatedAt ? (
          <span className="mt-0.5 block truncate font-mono text-[8px] text-zinc-700">
            {updatedAt}
          </span>
        ) : null}
      </div>
    </div>
  );
}
