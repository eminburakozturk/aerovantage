"use client";

import { Suspense } from "react";

import { OpsPageHeader } from "@/components/ops/ops-page-header";
import { PageLoading } from "@/components/ui/async-state";
import { AnnotationsProvider } from "@/components/ai/annotations-context";
import { WorkspaceTabs, useWorkspaceTab } from "@/components/workspace/workspace-tabs";
import { useTranslations } from "@/context/locale-context";
import { getDefaultTab, resolveWorkspaceTab, type WorkspaceMeta } from "@/lib/workspace-config";

interface WorkspaceShellProps {
  workspace: WorkspaceMeta;
  children: (tab: string) => React.ReactNode;
}

function WorkspaceShellInner({ workspace, children }: WorkspaceShellProps) {
  const defaultTab = getDefaultTab(workspace.id);
  const activeTab = useWorkspaceTab(workspace.id, defaultTab);
  const validTab = resolveWorkspaceTab(workspace, activeTab);

  return (
    <AnnotationsProvider context={workspace.id}>
      <div className="flex h-full min-h-0 flex-col overflow-hidden">
        <OpsPageHeader section={workspace.section} title={workspace.title} description={workspace.description} />
        <WorkspaceTabs tabs={workspace.tabs} activeTab={validTab} basePath={workspace.href} />

        <div className="min-h-0 flex-1 overflow-y-auto">
          <div className="ops-fade-in min-h-full p-2">{children(validTab)}</div>
        </div>
      </div>
    </AnnotationsProvider>
  );
}

export function WorkspaceShell(props: WorkspaceShellProps) {
  const { t } = useTranslations("ui");
  return (
    <Suspense fallback={<PageLoading label={t("commonUi.workspaceLoading")} />}>
      <WorkspaceShellInner {...props} />
    </Suspense>
  );
}
