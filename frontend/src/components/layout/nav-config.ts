import type { LucideIcon } from "lucide-react";
import {
  Activity,
  Bot,
  Cloud,
  FileText,
  History,
  Home,
  LineChart,
  Radio,
  Settings,
  ShieldAlert,
  TrendingUp,
  Wind,
  FlaskConical,
  BarChart3,
  Zap,
  Brain,
  Landmark,
  Factory,
} from "lucide-react";
import { APP_ROUTES } from "@/lib/routes";
import {
  WORKSPACE_IDS,
  WORKSPACE_LIST,
  WORKSPACES,
  getWorkspaceByPathname,
  type WorkspaceMeta,
} from "@/lib/workspace-config";

export interface NavItem {
  id: string;
  label: string;
  href: string;
  icon?: LucideIcon;
}

export interface NavSection {
  id: string;
  title: string;
  items: NavItem[];
}

type TranslateFn = (key: string, params?: Record<string, string | number>) => string;

const NAV_SECTION_DEFS: Array<{ id: string; titleKey: string; itemIds: string[] }> = [
  { id: "general", titleKey: "sections.general", itemIds: ["operations", "dashboard"] },
  {
    id: "forecast",
    titleKey: "sections.forecast",
    itemIds: ["forecast", "forecast-weather", "forecast-history"],
  },
  { id: "market", titleKey: "sections.market", itemIds: ["market-ptf", "market-smf", "market"] },
  { id: "risk", titleKey: "sections.risk", itemIds: ["risk", "risk-financial", "risk-production"] },
  { id: "ai", titleKey: "sections.ai", itemIds: ["ai", "ai-archive"] },
  { id: "operations", titleKey: "sections.operations", itemIds: ["assets", "scenarios", "reports"] },
  { id: "system", titleKey: "sections.system", itemIds: ["monitoring", "admin"] },
];

const NAV_ITEM_DEFS: Record<string, { labelKey: string; href: string; icon?: LucideIcon }> = {
  operations: { labelKey: "items.operations", href: APP_ROUTES.operations, icon: Radio },
  dashboard: { labelKey: "items.dashboard", href: APP_ROUTES.dashboard, icon: Home },
  forecast: { labelKey: "items.forecast", href: WORKSPACES[WORKSPACE_IDS.forecast].href, icon: LineChart },
  "forecast-weather": {
    labelKey: "items.forecast-weather",
    href: `${WORKSPACES[WORKSPACE_IDS.forecast].href}?tab=weather`,
    icon: Cloud,
  },
  "forecast-history": {
    labelKey: "items.forecast-history",
    href: `${WORKSPACES[WORKSPACE_IDS.forecast].href}?tab=history`,
    icon: History,
  },
  "market-ptf": {
    labelKey: "items.market-ptf",
    href: `${WORKSPACES[WORKSPACE_IDS.market].href}?tab=ptf`,
    icon: Zap,
  },
  "market-smf": {
    labelKey: "items.market-smf",
    href: `${WORKSPACES[WORKSPACE_IDS.market].href}?tab=smf`,
    icon: BarChart3,
  },
  market: { labelKey: "items.market", href: WORKSPACES[WORKSPACE_IDS.market].href, icon: TrendingUp },
  risk: { labelKey: "items.risk", href: WORKSPACES[WORKSPACE_IDS.risk].href, icon: ShieldAlert },
  "risk-financial": {
    labelKey: "items.risk-financial",
    href: `${WORKSPACES[WORKSPACE_IDS.risk].href}?tab=financial`,
    icon: Landmark,
  },
  "risk-production": {
    labelKey: "items.risk-production",
    href: `${WORKSPACES[WORKSPACE_IDS.risk].href}?tab=production`,
    icon: Factory,
  },
  ai: { labelKey: "items.ai", href: WORKSPACES[WORKSPACE_IDS.ai].href, icon: Brain },
  "ai-archive": {
    labelKey: "items.ai-archive",
    href: `${WORKSPACES[WORKSPACE_IDS.ai].href}?tab=archive`,
    icon: History,
  },
  assets: { labelKey: "items.assets", href: WORKSPACES[WORKSPACE_IDS.assets].href, icon: Wind },
  scenarios: {
    labelKey: "items.scenarios",
    href: WORKSPACES[WORKSPACE_IDS.scenarios].href,
    icon: FlaskConical,
  },
  reports: { labelKey: "items.reports", href: WORKSPACES[WORKSPACE_IDS.reports].href, icon: FileText },
  monitoring: {
    labelKey: "items.monitoring",
    href: WORKSPACES[WORKSPACE_IDS.monitoring].href,
    icon: Activity,
  },
  admin: { labelKey: "items.admin", href: WORKSPACES[WORKSPACE_IDS.settings].href, icon: Settings },
};

const MOBILE_NAV_DEFS = [
  { id: "operations", labelKey: "items.operations-mobile", href: APP_ROUTES.operations, icon: Radio },
  { id: "dashboard", labelKey: "items.dashboard-mobile", href: APP_ROUTES.dashboard, icon: Home },
  { id: "forecast", labelKey: "items.forecast-mobile", href: WORKSPACES[WORKSPACE_IDS.forecast].href, icon: LineChart },
  { id: "ai", labelKey: "items.ai-mobile", href: WORKSPACES[WORKSPACE_IDS.ai].href, icon: Bot },
  { id: "reports", labelKey: "items.reports-mobile", href: WORKSPACES[WORKSPACE_IDS.reports].href, icon: FileText },
];

const STEP_KEYS: Record<string, string> = {
  "0800_forecast": "steps.0800_forecast",
  "0801_performance_monitoring": "steps.0801_performance_monitoring",
  "0802_risk_calculation": "steps.0802_risk_calculation",
  "0803_alert_generation": "steps.0803_alert_generation",
  "0804_ai_explanation": "steps.0804_ai_explanation",
  "0805_dashboard_update": "steps.0805_dashboard_update",
};

export function buildNavSections(t: TranslateFn): NavSection[] {
  return NAV_SECTION_DEFS.map((section) => ({
    id: section.id,
    title: t(section.titleKey),
    items: section.itemIds.map((itemId) => {
      const def = NAV_ITEM_DEFS[itemId];
      return {
        id: itemId,
        label: t(def.labelKey),
        href: def.href,
        icon: def.icon,
      };
    }),
  }));
}

export function buildMobileNavItems(t: TranslateFn): NavItem[] {
  return MOBILE_NAV_DEFS.map((item) => ({
    id: item.id,
    label: t(item.labelKey),
    href: item.href,
    icon: item.icon,
  }));
}

export function formatStepLabel(t: TranslateFn, step: string): string {
  const key = STEP_KEYS[step];
  return key ? t(key) : step;
}

function buildWorkspacePageMeta(workspaces: WorkspaceMeta[]) {
  return Object.fromEntries(
    workspaces.map((workspace) => [
      workspace.href,
      {
        section: workspace.section,
        title: workspace.title,
        description: workspace.description,
      },
    ]),
  );
}

export function getPageMetaTranslated(
  t: TranslateFn,
  pathname: string,
  workspaces?: WorkspaceMeta[],
) {
  const workspaceMeta = buildWorkspacePageMeta(workspaces ?? WORKSPACE_LIST);
  const PAGE_META: Record<string, { section: string; title: string; description: string }> = {
    [APP_ROUTES.dashboard]: {
      section: t("pages.dashboard.section"),
      title: t("pages.dashboard.title"),
      description: t("pages.dashboard.description"),
    },
    [APP_ROUTES.operations]: {
      section: t("pages.operations.section"),
      title: t("pages.operations.title"),
      description: t("pages.operations.description"),
    },
    [APP_ROUTES.activity]: {
      section: t("pages.activity.section"),
      title: t("pages.activity.title"),
      description: t("pages.activity.description"),
    },
    ...workspaceMeta,
  };

  const base = pathname.split("?")[0].split("#")[0];
  if (PAGE_META[base]) return PAGE_META[base];
  for (const [path, meta] of Object.entries(PAGE_META)) {
    if (path !== "/" && base.startsWith(path)) return meta;
  }
  return {
    section: t("pages.fallback.section"),
    title: t("pages.fallback.title"),
    description: t("pages.fallback.description"),
  };
}

export function isNavActive(pathname: string, href: string): boolean {
  const [path] = href.split("?");
  const pathClean = path.split("#")[0];
  if (pathClean === APP_ROUTES.dashboard) return pathname === APP_ROUTES.dashboard;
  return pathname === pathClean || pathname.startsWith(`${pathClean}/`);
}

export function isNavItemActive(
  pathname: string,
  searchParams: URLSearchParams,
  href: string,
): boolean {
  const [path, queryPart] = href.split("?");
  const pathClean = path.split("#")[0];
  const pathMatch =
    pathClean === APP_ROUTES.dashboard
      ? pathname === APP_ROUTES.dashboard
      : pathname === pathClean || pathname.startsWith(`${pathClean}/`);
  if (!pathMatch) return false;

  if (!queryPart) {
    const tab = searchParams.get("tab");
    const workspace = getWorkspaceByPathname(pathClean);
    const defaultTab = workspace?.tabs[0]?.id;
    if (defaultTab && tab && tab !== defaultTab) return false;
    return true;
  }

  const hrefParams = new URLSearchParams(queryPart);
  for (const [key, value] of hrefParams.entries()) {
    if (searchParams.get(key) !== value) return false;
  }
  return true;
}

export function getActiveSectionId(pathname: string, sections: NavSection[]): string | null {
  for (const section of sections) {
    if (section.items.some((item) => isNavActive(pathname, item.href))) {
      return section.id;
    }
  }
  return null;
}
