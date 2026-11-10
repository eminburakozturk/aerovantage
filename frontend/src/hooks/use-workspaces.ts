"use client";

import { useMemo } from "react";

import { useTranslations } from "@/context/locale-context";
import {
  WORKSPACE_IDS,
  buildWorkspaces,
  getWorkspaceTranslated,
  type WorkspaceId,
} from "@/lib/workspace-config";

export function useWorkspaces() {
  const { t } = useTranslations("workspaces");

  return useMemo(() => buildWorkspaces(t), [t]);
}

export function useWorkspace(workspaceId: WorkspaceId) {
  const { t } = useTranslations("workspaces");
  return useMemo(() => getWorkspaceTranslated(t, workspaceId), [t, workspaceId]);
}

export { WORKSPACE_IDS };
