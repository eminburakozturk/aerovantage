import { cn } from "@/lib/utils";

type StatusLevel = "ok" | "warn" | "crit" | "idle";

const DOT: Record<StatusLevel, string> = {
  ok: "bg-emerald-400",
  warn: "bg-amber-400",
  crit: "bg-rose-500",
  idle: "bg-zinc-600",
};

const LABEL: Record<StatusLevel, string> = {
  ok: "text-emerald-400",
  warn: "text-amber-400",
  crit: "text-rose-400",
  idle: "text-zinc-500",
};

interface StatusIndicatorProps {
  status: StatusLevel;
  label: string;
  className?: string;
}

export function StatusIndicator({ status, label, className }: StatusIndicatorProps) {
  return (
    <span className={cn("inline-flex items-center gap-1.5", className)}>
      <span className={cn("h-1.5 w-1.5 shrink-0", DOT[status])} aria-hidden />
      <span className={cn("text-[10px]", LABEL[status])}>{label}</span>
    </span>
  );
}
