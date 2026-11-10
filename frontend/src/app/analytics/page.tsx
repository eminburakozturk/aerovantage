import { redirect } from "next/navigation";
import { WORKSPACE_IDS, WORKSPACES } from "@/lib/workspace-config";

export default function AnalyticsRedirect() {
  redirect(WORKSPACES[WORKSPACE_IDS.forecast].href);
}
