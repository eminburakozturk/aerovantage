import { redirect } from "next/navigation";
import { WORKSPACE_IDS, WORKSPACES } from "@/lib/workspace-config";

export default function RecommendationsRedirect() {
  redirect(WORKSPACES[WORKSPACE_IDS.ai].href);
}
