"use client";

import { ForecastWorkspace } from "@/components/workspace/forecast-workspace";
import { WorkspaceShell } from "@/components/workspace/workspace-shell";
import { useWorkspaceData } from "@/hooks/use-workspace-data";
import { useWorkspace, WORKSPACE_IDS } from "@/hooks/use-workspaces";

export default function ForecastPage() {
  const { data, history, loading, error } = useWorkspaceData();
  const workspace = useWorkspace(WORKSPACE_IDS.forecast);

  return (
    <WorkspaceShell workspace={workspace}>
      {(tab) => <ForecastWorkspace tab={tab} data={data} history={history} loading={loading} error={error} />}
    </WorkspaceShell>
  );
}
