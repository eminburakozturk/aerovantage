"use client";

import { RiskWorkspace } from "@/components/workspace/risk-workspace";
import { WorkspaceShell } from "@/components/workspace/workspace-shell";
import { useWorkspaceData } from "@/hooks/use-workspace-data";
import { useWorkspace, WORKSPACE_IDS } from "@/hooks/use-workspaces";

export default function RiskPage() {
  const { data, history, loading, error } = useWorkspaceData();
  const workspace = useWorkspace(WORKSPACE_IDS.risk);

  return (
    <WorkspaceShell workspace={workspace}>
      {(tab) => <RiskWorkspace tab={tab} data={data} history={history} loading={loading} error={error} />}
    </WorkspaceShell>
  );
}
