"use client";

import { ScenariosWorkspace } from "@/components/workspace/scenarios-workspace";
import { WorkspaceShell } from "@/components/workspace/workspace-shell";
import { useWorkspace, WORKSPACE_IDS } from "@/hooks/use-workspaces";

export default function ScenariosPage() {
  const workspace = useWorkspace(WORKSPACE_IDS.scenarios);

  return (
    <WorkspaceShell workspace={workspace}>
      {(tab) => <ScenariosWorkspace tab={tab} />}
    </WorkspaceShell>
  );
}
