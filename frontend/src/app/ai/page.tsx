"use client";

import { Suspense } from "react";

import { PageLoading } from "@/components/ui/async-state";
import { AiWorkspace } from "@/components/workspace/ai-workspace";
import { WorkspaceShell } from "@/components/workspace/workspace-shell";
import { useTranslations } from "@/context/locale-context";
import { useWorkspaceData } from "@/hooks/use-workspace-data";
import { useWorkspace, WORKSPACE_IDS } from "@/hooks/use-workspaces";

function AiPageInner() {
  const { data, history, loading, error } = useWorkspaceData();
  const workspace = useWorkspace(WORKSPACE_IDS.ai);

  return (
    <WorkspaceShell workspace={workspace}>
      {(tab) => (
        <AiWorkspace tab={tab} data={data} history={history} loading={loading} error={error} />
      )}
    </WorkspaceShell>
  );
}

function AiPageFallback() {
  const { t } = useTranslations("ui");
  return <PageLoading label={t("activity.aiWorkspaceLoading")} />;
}

export default function AiPage() {
  return (
    <Suspense fallback={<AiPageFallback />}>
      <AiPageInner />
    </Suspense>
  );
}
