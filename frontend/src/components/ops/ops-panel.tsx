import { cn } from "@/lib/utils";

interface OpsPanelProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  meta?: string;
  action?: React.ReactNode;
  noPadding?: boolean;
  id?: string;
  /** comfortable: daha okunabilir alt paneller için */
  density?: "default" | "comfortable";
}

export function OpsPanel({
  children,
  className,
  title,
  meta,
  action,
  noPadding,
  id,
  density = "default",
}: OpsPanelProps) {
  const comfortable = density === "comfortable";

  return (
    <section
      id={id}
      className={cn(
        "flex min-h-0 flex-col border border-[#27272A] bg-[#18181B] transition-colors duration-200",
        className,
      )}
    >
      {title ? (
        <header
          className={cn(
            "flex shrink-0 items-center justify-between gap-2 border-b border-[#27272A]",
            comfortable ? "px-3 py-2" : "px-2 py-1.5",
          )}
        >
          <div className="min-w-0">
            <h2
              className={cn(
                "truncate font-semibold uppercase tracking-[0.08em] text-zinc-300",
                comfortable ? "text-[11px]" : "text-[10px] text-zinc-400",
              )}
            >
              {title}
            </h2>
            {meta ? (
              <p
                className={cn(
                  "truncate font-mono text-zinc-600",
                  comfortable ? "text-[10px]" : "text-[9px]",
                )}
              >
                {meta}
              </p>
            ) : null}
          </div>
          {action}
        </header>
      ) : null}
      <div className={cn("min-h-0 flex-1", !noPadding && (comfortable ? "p-3" : "p-2"))}>
        {children}
      </div>
    </section>
  );
}
