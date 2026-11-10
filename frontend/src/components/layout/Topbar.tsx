"use client";

import { Bell, ChevronDown, Play, RefreshCw, User } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { BrandLogo } from "@/components/brand/brand-logo";
import { StatusIndicator } from "@/components/ops/status-indicator";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useOperasyon } from "@/context/operasyon-context";
import { useTranslations } from "@/context/locale-context";
import { useNavConfig } from "@/hooks/use-nav-config";
import { normalizeSeverity, STATUS_COLORS } from "@/lib/status-level";
import { cn } from "@/lib/utils";
import { APP_ROUTES } from "@/lib/routes";
import { WORKSPACE_IDS, WORKSPACES } from "@/lib/workspace-config";
import { PipelineFeedBadge } from "./pipeline-feed-badge";
import { QuickActionHub } from "@/components/platform/quick-action-hub";

interface TopbarProps {
  className?: string;
  onRunPipeline?: () => void;
  pipelineRunning?: boolean;
  systemStatus?: "ok" | "warn" | "crit" | "idle";
}

function notificationColor(level: string): string {
  const normalized = normalizeSeverity(level);
  return STATUS_COLORS[normalized].text;
}

export function Topbar({
  className,
  onRunPipeline,
  pipelineRunning,
  systemStatus = "ok",
}: TopbarProps) {
  const pathname = usePathname();
  const { getPageMeta } = useNavConfig();
  const { t, bcp47 } = useTranslations("topbar");
  const meta = getPageMeta(pathname);
  const [clock, setClock] = useState("");
  const {
    assets,
    selectedAssetId,
    setSelectedAssetId,
    notifications,
    assetsLoading,
    assetsError,
    reloadAssets,
    pipelineFeedState,
    scadaIsMock,
  } = useOperasyon();

  const selectedAsset = assets.find((a) => a.id === selectedAssetId) ?? assets[0];

  useEffect(() => {
    const tick = () => {
      setClock(
        new Date().toLocaleTimeString(bcp47, {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }),
      );
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [bcp47]);

  const statusLabel =
    systemStatus === "ok"
      ? t("systemActive")
      : systemStatus === "warn"
        ? scadaIsMock
          ? t("systemMockDegraded")
          : t("systemWarn")
        : systemStatus === "crit"
          ? scadaIsMock
            ? t("systemMockDegraded")
            : t("systemCrit")
          : t("systemIdle");

  return (
    <header
      className={cn(
        "flex h-10 shrink-0 items-center gap-3 border-b border-[#27272A] bg-[#09090B] px-3",
        className,
      )}
    >
      <BrandLogo variant="compact" href="/" className="min-w-0 shrink lg:hidden" />

      <div className="hidden min-w-0 flex-1 md:block">
        <p className="text-[9px] font-semibold uppercase tracking-[0.08em] text-zinc-600">
          {meta.section}
        </p>
        <p className="truncate text-xs font-medium text-zinc-200">{meta.title}</p>
      </div>

      <div className="hidden items-center gap-3 lg:flex">
        <StatusIndicator status={systemStatus} label={statusLabel} />
        <span className="font-mono text-[10px] tabular-nums text-zinc-500">{clock}</span>
      </div>

      <div className="ml-auto flex items-center gap-1">
        <QuickActionHub />

        {pathname.startsWith(APP_ROUTES.operations) && onRunPipeline ? (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-7 rounded-none border border-[#27272A] px-2 text-[10px] text-zinc-300 hover:bg-[#18181B] hover:text-zinc-100"
            onClick={onRunPipeline}
            disabled={pipelineRunning || !selectedAssetId}
          >
            <Play className="mr-1 h-3 w-3" />
            {t("pipeline")}
            <span className="mx-1 text-zinc-700" aria-hidden>
              ·
            </span>
            <PipelineFeedBadge state={pipelineFeedState} />
          </Button>
        ) : null}

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="relative h-7 w-7 rounded-none text-zinc-500 hover:bg-[#18181B] hover:text-zinc-200"
              aria-label={t("notifications")}
            >
              <Bell className="h-3.5 w-3.5" strokeWidth={1.75} />
              {notifications.length > 0 ? (
                <span className="absolute right-1 top-1 h-1.5 w-1.5 bg-rose-500" />
              ) : null}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-72 rounded-none border-[#27272A] bg-[#18181B]">
            <DropdownMenuLabel className="text-[10px] text-zinc-500">{t("activeNotifications")}</DropdownMenuLabel>
            <DropdownMenuSeparator className="bg-[#27272A]" />
            {notifications.length === 0 ? (
              <DropdownMenuItem disabled className="text-xs">
                {t("noNotifications")}
              </DropdownMenuItem>
            ) : (
              notifications.map((item, index) => (
                <DropdownMenuItem
                  key={`${item.title}-${index}`}
                  className="flex flex-col items-start gap-0.5 rounded-none"
                >
                  <span className={cn("text-[11px] font-medium", notificationColor(item.level))}>
                    {item.title}
                  </span>
                  <span className="text-[10px] text-zinc-500">{item.message}</span>
                </DropdownMenuItem>
              ))
            )}
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              className="h-7 max-w-[140px] gap-1 rounded-none px-2 text-zinc-400 hover:bg-[#18181B] hover:text-zinc-100"
              disabled={assetsLoading || assets.length === 0}
            >
              <span className="truncate text-[10px]">{selectedAsset?.name ?? t("plant")}</span>
              <ChevronDown className="h-3 w-3 shrink-0" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-52 rounded-none border-[#27272A] bg-[#18181B]">
            <DropdownMenuLabel className="text-[10px] text-zinc-500">{t("portfolio")}</DropdownMenuLabel>
            <DropdownMenuSeparator className="bg-[#27272A]" />
            {assetsError ? (
              <DropdownMenuItem disabled>{assetsError}</DropdownMenuItem>
            ) : (
              assets.map((asset) => (
                <DropdownMenuItem
                  key={asset.id}
                  onClick={() => setSelectedAssetId(asset.id)}
                  className={cn(
                    "flex flex-col items-start rounded-none",
                    selectedAssetId === asset.id && "bg-[#27272A]/40",
                  )}
                >
                  <span className="text-[11px] text-zinc-200">{asset.name}</span>
                  <span className="font-mono text-[9px] text-zinc-600">
                    {asset.id} · {asset.capacity_mw} MW
                  </span>
                </DropdownMenuItem>
              ))
            )}
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 rounded-none p-0 hover:bg-[#18181B]"
              aria-label={t("profile")}
            >
              <Avatar className="h-6 w-6 rounded-none">
                <AvatarFallback className="rounded-none bg-transparent text-[9px] text-zinc-400">
                  <User className="h-3 w-3" />
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-44 rounded-none border-[#27272A] bg-[#18181B]">
            <DropdownMenuLabel className="text-[10px] text-zinc-500">{t("operator")}</DropdownMenuLabel>
            <DropdownMenuSeparator className="bg-[#27272A]" />
            <DropdownMenuItem asChild className="rounded-none text-xs">
              <Link href={APP_ROUTES.dashboard}>{t("dashboard")}</Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild className="rounded-none text-xs">
              <Link href={APP_ROUTES.operations}>{t("operations")}</Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild className="rounded-none text-xs">
              <Link href={WORKSPACES[WORKSPACE_IDS.reports].href}>{t("reports")}</Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild className="rounded-none text-xs">
              <Link href={WORKSPACES[WORKSPACE_IDS.ai].href}>{t("aiCenter")}</Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild className="rounded-none text-xs">
              <Link href={WORKSPACES[WORKSPACE_IDS.settings].href}>{t("admin")}</Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator className="bg-[#27272A]" />
            <DropdownMenuItem onClick={() => void reloadAssets()} className="rounded-none text-xs">
              <RefreshCw className="mr-2 h-3 w-3" />
              {t("reloadAssets")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
