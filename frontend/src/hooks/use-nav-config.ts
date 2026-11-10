"use client";

import { useMemo } from "react";

import { useTranslations } from "@/context/locale-context";
import {
  buildMobileNavItems,
  buildNavSections,
  getPageMetaTranslated,
  formatStepLabel,
} from "@/components/layout/nav-config";
import { buildWorkspaces } from "@/lib/workspace-config";

export function useNavConfig() {
  const { t } = useTranslations("nav");
  const { t: tw } = useTranslations("workspaces");

  const workspaceList = useMemo(() => Object.values(buildWorkspaces(tw)), [tw]);

  return useMemo(
    () => ({
      sections: buildNavSections(t),
      mobileItems: buildMobileNavItems(t),
      formatStep: (step: string) => formatStepLabel(t, step),
      getPageMeta: (pathname: string) => getPageMetaTranslated(t, pathname, workspaceList),
    }),
    [t, workspaceList],
  );
}
