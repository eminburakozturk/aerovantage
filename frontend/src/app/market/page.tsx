"use client";

import { MarketWorkspace } from "@/components/workspace/market-workspace";
import { WorkspaceShell } from "@/components/workspace/workspace-shell";
import { useWorkspaceData } from "@/hooks/use-workspace-data";
import { useWorkspace, WORKSPACE_IDS } from "@/hooks/use-workspaces";

export default function MarketPage() {
  const { data, history, kpi, loading, error } = useWorkspaceData();
  const workspace = useWorkspace(WORKSPACE_IDS.market);

  return (
    <WorkspaceShell workspace={workspace}>
      {(tab) => <MarketWorkspace tab={tab} data={data} history={history} kpi={kpi} loading={loading} error={error} />}
    </WorkspaceShell>
  );
}
