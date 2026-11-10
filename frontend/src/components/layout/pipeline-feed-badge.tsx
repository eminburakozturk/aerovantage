"use client";

import { useTranslations } from "@/context/locale-context";
import {
  PIPELINE_FEED_STYLES,
  type PipelineFeedState,
} from "@/lib/pipeline-feed-state";
import { cn } from "@/lib/utils";

interface PipelineFeedBadgeProps {
  state: PipelineFeedState;
  className?: string;
}

export function PipelineFeedBadge({ state, className }: PipelineFeedBadgeProps) {
  const { t } = useTranslations("ui");
  const style = PIPELINE_FEED_STYLES[state];

  return (
    <span className={cn("inline-flex items-center gap-1", style.text, className)}>
      <span
        className={cn("h-1.5 w-1.5 rounded-full", style.dot, style.pulse && "animate-pulse")}
        aria-hidden
      />
      {t(`pipelineFeed.${state}`)}
    </span>
  );
}
