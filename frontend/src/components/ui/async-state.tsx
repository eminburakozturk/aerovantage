"use client";

import Image from "next/image";
import { AlertCircle, Inbox, Loader2, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useTranslations } from "@/context/locale-context";
import { useUserMessages } from "@/lib/user-messages";
import { cn } from "@/lib/utils";

interface ErrorBannerProps {
  message: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorBanner({ message, onRetry, className }: ErrorBannerProps) {
  const { t } = useTranslations("async");
  const { friendlyError } = useUserMessages();

  return (
    <div
      className={cn(
        "flex items-start gap-3 border border-rose-500/30 bg-rose-950/20 px-3 py-2.5 transition-opacity duration-200",
        className,
      )}
      role="alert"
    >
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="text-[11px] font-medium text-rose-200">{t("errorTitle")}</p>
        <p className="mt-0.5 text-[11px] leading-relaxed text-rose-300/90">{friendlyError(message)}</p>
      </div>
      {onRetry ? (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onRetry}
          className="h-7 shrink-0 rounded-none border border-rose-500/20 px-2 text-[10px] text-rose-300 hover:bg-rose-950/40"
        >
          <RefreshCw className="mr-1 h-3 w-3" />
          {t("retry")}
        </Button>
      ) : null}
    </div>
  );
}

interface EmptyStateProps {
  title?: string;
  message: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ title, message, action, className }: EmptyStateProps) {
  const { t } = useTranslations("async");

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center border border-dashed border-[#27272A] bg-[#141416]/50 px-6 py-10 text-center",
        className,
      )}
    >
      <Inbox className="mb-3 h-8 w-8 text-zinc-600" strokeWidth={1.25} aria-hidden />
      <p className="text-[12px] font-medium text-zinc-300">{title ?? t("emptyTitle")}</p>
      <p className="mt-1.5 max-w-sm text-[11px] leading-relaxed text-zinc-500">{message}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

interface LoadingBlockProps {
  label?: string;
  rows?: number;
  className?: string;
}

export function LoadingBlock({ label, rows = 4, className }: LoadingBlockProps) {
  const { t } = useTranslations("async");

  return (
    <div className={cn("space-y-2", className)} aria-busy aria-live="polite">
      <div className="flex items-center gap-2 text-[11px] text-zinc-500">
        <Loader2 className="h-3.5 w-3.5 animate-spin text-[#3B82F6]" aria-hidden />
        <span>{label ?? t("loadingData")}</span>
      </div>
      <div className="space-y-1.5">
        {Array.from({ length: rows }).map((_, i) => (
          <div
            key={i}
            className="h-12 animate-pulse border border-[#27272A] bg-[#18181B]"
            style={{ animationDelay: `${i * 60}ms` }}
          />
        ))}
      </div>
    </div>
  );
}

export function PageLoading({ label }: { label?: string }) {
  const { t } = useTranslations("async");

  return (
    <div className="flex h-full min-h-[200px] flex-col items-center justify-center gap-3 p-6">
      <Image
        src="/brand/logo-mark.png"
        alt=""
        width={48}
        height={44}
        className="h-10 w-auto animate-pulse bg-transparent object-contain opacity-90"
        aria-hidden
      />
      <p className="text-[11px] text-zinc-500">{label ?? t("loadingPage")}</p>
      <div className="h-1 w-32 overflow-hidden bg-[#27272A]">
        <div className="h-full w-1/2 animate-pulse bg-[#00B8FF]/60" />
      </div>
    </div>
  );
}
