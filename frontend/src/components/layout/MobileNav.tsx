"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";
import { useNavConfig } from "@/hooks/use-nav-config";

import { isNavActive } from "./nav-config";

interface MobileNavProps {
  className?: string;
}

export function MobileNav({ className }: MobileNavProps) {
  const pathname = usePathname();
  const { mobileItems } = useNavConfig();

  return (
    <nav
      className={cn(
        "fixed inset-x-0 bottom-0 z-40 flex h-12 items-stretch border-t border-[#27272A] bg-[#0C0C0E] lg:hidden",
        className,
      )}
    >
      {mobileItems.map((item) => {
        const Icon = item.icon;
        const active = isNavActive(pathname, item.href);

        return (
          <Link
            key={item.id}
            href={item.href}
            className={cn(
              "flex flex-1 flex-col items-center justify-center gap-0.5 border-t-2 text-[9px]",
              active ? "border-t-[#00B8FF] text-zinc-100" : "border-t-transparent text-zinc-600",
            )}
          >
            {Icon ? <Icon className="h-4 w-4" strokeWidth={1.75} /> : null}
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
