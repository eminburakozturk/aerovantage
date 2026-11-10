"use client";

import { Suspense } from "react";

import { ReportsWorkspace } from "@/components/workspace/reports-workspace";
import { WorkspaceShell } from "@/components/workspace/workspace-shell";
import { useWorkspaceData } from "@/hooks/use-workspace-data";
import { useWorkspace, WORKSPACE_IDS } from "@/hooks/use-workspaces";

function ReportsPageInner() {
  const { history } = useWorkspaceData();
  const workspace = useWorkspace(WORKSPACE_IDS.reports);

  return (
    <WorkspaceShell workspace={workspace}>
      {(tab) => <ReportsWorkspace tab={tab} history={history} />}
    </WorkspaceShell>
  );
}

export default function ReportsPage() {
  return (
    <Suspense fallback={<div className="p-4 text-[11px] text-zinc-500">…</div>}>
      <ReportsPageInner />
    </Suspense>
  );
}
