"use client";

import { ErrorBanner } from "@/components/ui/async-state";
import { TooltipProvider } from "@/components/ui/tooltip";
import { LocaleProvider } from "@/context/locale-context";
import { OperasyonProvider, useOperasyon } from "@/context/operasyon-context";

import { MobileNav } from "./MobileNav";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

function ShellChrome({ children }: { children: React.ReactNode }) {
  const { runPipeline, pipelineRunning, systemStatus, pipelineError, clearPipelineError } =
    useOperasyon();

  return (
    <div className="flex h-screen overflow-hidden bg-[#09090B] text-zinc-50">
      <Sidebar className="hidden lg:flex" />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          onRunPipeline={() => void runPipeline()}
          pipelineRunning={pipelineRunning}
          systemStatus={systemStatus}
        />
        {pipelineError ? (
          <div className="shrink-0 border-b border-[#27272A] px-3 py-2 lg:px-4">
            <ErrorBanner message={pipelineError} onRetry={clearPipelineError} />
          </div>
        ) : null}
        <main className="min-h-0 flex-1 overflow-y-auto pb-12 lg:pb-0">
          <div className="flex min-h-full flex-col">{children}</div>
        </main>
      </div>

      <MobileNav className="lg:hidden" />
    </div>
  );
}

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <LocaleProvider>
      <OperasyonProvider>
        <TooltipProvider delayDuration={0}>
          <ShellChrome>{children}</ShellChrome>
        </TooltipProvider>
      </OperasyonProvider>
    </LocaleProvider>
  );
}
