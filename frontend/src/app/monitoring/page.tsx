"use client";

import { MonitoringWorkspace } from "@/components/workspace/monitoring-workspace";
import { WorkspaceShell } from "@/components/workspace/workspace-shell";
import { useWorkspaceData } from "@/hooks/use-workspace-data";
import { useWorkspace, WORKSPACE_IDS } from "@/hooks/use-workspaces";

export default function MonitoringPage() {
  const { health, kpi, history, loading, error } = useWorkspaceData();
  const workspace = useWorkspace(WORKSPACE_IDS.monitoring);

  return (
    <WorkspaceShell workspace={workspace}>
      {(tab) => (
        <MonitoringWorkspace tab={tab} health={health} kpi={kpi} history={history} loading={loading} error={error} />
      )}
    </WorkspaceShell>
  );
}
