"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

import { cn } from "@/lib/utils";
import type { WorkspaceTab } from "@/lib/workspace-config";

interface WorkspaceTabsProps {
  tabs: WorkspaceTab[];
  activeTab: string;
  basePath: string;
  className?: string;
}

export function WorkspaceTabs({ tabs, activeTab, basePath, className }: WorkspaceTabsProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const setTab = useCallback(
    (tabId: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (tabId === tabs[0]?.id) {
        params.delete("tab");
      } else {
        params.set("tab", tabId);
      }
      const qs = params.toString();
      router.replace(qs ? `${basePath}?${qs}` : basePath, { scroll: false });
    },
    [router, searchParams, basePath, tabs],
  );

  return (
    <div className={cn("flex shrink-0 gap-0 border-b border-[#27272A] bg-[#0C0C0E]", className)}>
      {tabs.map((tab) => {
        const active = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => setTab(tab.id)}
            className={cn(
              "border-b-2 px-3 py-2 text-[10px] font-medium transition-colors duration-200",
              active
                ? "border-b-[#3B82F6] text-zinc-100"
                : "border-b-transparent text-zinc-600 hover:text-zinc-400",
            )}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}

export function useWorkspaceTab(workspaceId: string, defaultTab: string): string {
  const searchParams = useSearchParams();
  return searchParams.get("tab") ?? defaultTab;
}
