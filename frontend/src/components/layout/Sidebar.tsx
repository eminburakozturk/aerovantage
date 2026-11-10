"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { ChevronRight } from "lucide-react";
import { Suspense, useEffect, useState } from "react";

import { BrandLogo } from "@/components/brand/brand-logo";
import { cn } from "@/lib/utils";
import { useTranslations } from "@/context/locale-context";
import { useNavConfig } from "@/hooks/use-nav-config";
import { rememberWorkspace } from "@/lib/report-types";

import { getActiveSectionId, isNavItemActive, type NavItem } from "./nav-config";

function workspaceFromPath(pathname: string): string {
  if (pathname === "/" || pathname === "") return "dashboard";
  const seg = pathname.split("/").filter(Boolean)[0] ?? "dashboard";
  if (seg === "operations") return "operations";
  return seg;
}

interface SidebarProps {
  className?: string;
}

function NavLinkItem({ item, pathname }: { item: NavItem; pathname: string }) {
  const searchParams = useSearchParams();
  const active = isNavItemActive(pathname, searchParams, item.href);
  const Icon = item.icon;

  return (
    <Link
      href={item.href}
      className={cn(
        "flex items-center gap-2 border-l-2 py-2 pl-4 pr-3 text-[11px] transition-colors",
        active
          ? "border-l-[#3B82F6] bg-[#18181B] font-medium text-zinc-50"
          : "border-l-transparent text-zinc-500 hover:bg-[#141416] hover:text-zinc-300",
      )}
    >
      {Icon ? <Icon className="h-3.5 w-3.5 shrink-0" strokeWidth={1.75} /> : null}
      <span className="truncate leading-tight">{item.label}</span>
    </Link>
  );
}

function SidebarNav({ className }: SidebarProps) {
  const pathname = usePathname();
  useEffect(() => {
    rememberWorkspace(workspaceFromPath(pathname));
  }, [pathname]);
  const searchParams = useSearchParams();
  const { sections } = useNavConfig();
  const { t } = useTranslations("common");
  const activeSection = getActiveSectionId(pathname, sections);

  const [openSections, setOpenSections] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(
      sections.map((s) => [s.id, s.id === "general" || s.id === activeSection]),
    ),
  );

  useEffect(() => {
    if (activeSection) {
      setOpenSections((prev) => ({ ...prev, [activeSection]: true }));
    }
  }, [activeSection]);

  const toggle = (id: string) => {
    setOpenSections((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <aside
      className={cn(
        "flex h-full w-[220px] shrink-0 flex-col border-r border-[#27272A] bg-[#0C0C0E]",
        className,
      )}
    >
      <div className="flex h-10 shrink-0 items-center border-b border-[#27272A] bg-[#09090B] px-2.5">
        <BrandLogo variant="compact" priority className="min-w-0" />
      </div>

      <nav className="flex-1 overflow-y-auto py-1.5">
        {sections.map((section) => {
          const isOpen = openSections[section.id] ?? false;
          const hasActive = section.items.some((item) =>
            isNavItemActive(pathname, searchParams, item.href),
          );

          return (
            <div key={section.id} className="mb-0.5">
              <button
                type="button"
                onClick={() => toggle(section.id)}
                className={cn(
                  "flex w-full items-center gap-1 px-3 py-2 text-left",
                  hasActive ? "text-zinc-300" : "text-zinc-600",
                )}
              >
                <ChevronRight
                  className={cn("h-3 w-3 shrink-0 transition-transform", isOpen && "rotate-90")}
                  strokeWidth={2}
                />
                <span className="text-[9px] font-bold uppercase tracking-[0.14em]">{section.title}</span>
              </button>

              {isOpen ? (
                <div className="mt-0.5 space-y-px">
                  {section.items.map((item) => (
                    <NavLinkItem key={item.id} item={item} pathname={pathname} />
                  ))}
                </div>
              ) : null}
            </div>
          );
        })}
      </nav>

      <div className="shrink-0 border-t border-[#27272A] px-3 py-2">
        <p className="font-mono text-[9px] text-zinc-600">{t("version")} · {t("edition")}</p>
      </div>
    </aside>
  );
}

export function Sidebar(props: SidebarProps) {
  return (
    <Suspense fallback={<aside className="w-[220px] shrink-0 border-r border-[#27272A] bg-[#0C0C0E]" />}>
      <SidebarNav {...props} />
    </Suspense>
  );
}
