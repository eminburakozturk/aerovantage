import { cn } from "@/lib/utils";

interface OpsPageHeaderProps {
  section: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
}

export function OpsPageHeader({ section, title, description, actions, className }: OpsPageHeaderProps) {
  return (
    <header
      className={cn(
        "flex shrink-0 flex-wrap items-end justify-between gap-2 border-b border-[#27272A] bg-[#0C0C0E] px-3 py-2",
        className,
      )}
    >
      <div className="min-w-0">
        <p className="text-[9px] font-semibold uppercase tracking-[0.1em] text-zinc-600">{section}</p>
        <h1 className="text-sm font-semibold text-zinc-100">{title}</h1>
        {description ? <p className="mt-0.5 text-[11px] text-zinc-500">{description}</p> : null}
      </div>
      {actions}
    </header>
  );
}
