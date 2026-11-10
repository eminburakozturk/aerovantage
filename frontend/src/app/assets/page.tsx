"use client";

import { AssetsWorkspace } from "@/components/workspace/assets-workspace";
import { WorkspaceShell } from "@/components/workspace/workspace-shell";
import { useWorkspaceData } from "@/hooks/use-workspace-data";
import { useWorkspace, WORKSPACE_IDS } from "@/hooks/use-workspaces";

export default function AssetsPage() {
  const { history } = useWorkspaceData();
  const workspace = useWorkspace(WORKSPACE_IDS.assets);

  return (
    <WorkspaceShell workspace={workspace}>
      {(tab) => <AssetsWorkspace tab={tab} history={history} />}
    </WorkspaceShell>
  );
}
