"use client";

import { useRouter } from "next/navigation";
import { FileText, Play, RefreshCw, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useOperasyon } from "@/context/operasyon-context";
import { useTranslations } from "@/context/locale-context";
import { WORKSPACE_IDS, WORKSPACES } from "@/lib/workspace-config";

interface QuickActionHubProps {
  onRefresh?: () => void;
  refreshing?: boolean;
}

/** Topbar için kompakt hızlı işlem satırı */
export function QuickActionHub({ onRefresh, refreshing }: QuickActionHubProps) {
  const router = useRouter();
  const { runPipeline, pipelineRunning, selectedAssetId, refreshLiveData, liveRefreshing } =
    useOperasyon();
  const { t } = useTranslations("ui");

  const handleRefresh = () => {
    if (onRefresh) {
      onRefresh();
      return;
    }
    void refreshLiveData().then(() => {
      router.refresh();
    });
  };

  return (
    <div className="hidden flex-col items-end md:flex">
      <div className="flex items-center gap-0.5">
        <ActionBtn
          icon={RefreshCw}
          label={t("quickActions.refresh")}
          onClick={handleRefresh}
          disabled={refreshing ?? liveRefreshing}
        />
        <ActionBtn
          icon={Play}
          label={t("quickActions.forecast")}
          onClick={() => void runPipeline()}
          disabled={pipelineRunning || !selectedAssetId}
        />
        <ActionBtn icon={FileText} label={t("quickActions.report")} onClick={() => router.push(WORKSPACES[WORKSPACE_IDS.reports].href)} />
        <ActionBtn
          icon={Sparkles}
          label={t("quickActions.ai")}
          onClick={() => router.push(WORKSPACES[WORKSPACE_IDS.ai].href)}
          iconClassName="text-[#38BDF8]"
          labelClassName="text-[#38BDF8]"
        />
      </div>
    </div>
  );
}

function ActionBtn({
  icon: Icon,
  label,
  onClick,
  disabled,
  iconClassName,
  labelClassName,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  iconClassName?: string;
  labelClassName?: string;
}) {
  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      disabled={disabled}
      onClick={onClick}
      className="h-7 rounded-none px-2 text-[9px] text-zinc-500 hover:bg-[#18181B] hover:text-zinc-200"
    >
      <Icon className={`mr-1 h-3 w-3 ${iconClassName ?? ""}`} />
      <span className={labelClassName}>{label}</span>
    </Button>
  );
}
