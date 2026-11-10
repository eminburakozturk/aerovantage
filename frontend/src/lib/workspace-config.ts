export interface WorkspaceTab {
  id: string;
  label: string;
}

export interface WorkspaceMeta {
  id: string;
  section: string;
  title: string;
  description: string;
  href: string;
  tabs: WorkspaceTab[];
}

export const WORKSPACE_IDS = {
  forecast: "forecast",
  market: "market",
  risk: "risk",
  ai: "ai",
  reports: "reports",
  assets: "assets",
  monitoring: "monitoring",
  scenarios: "scenarios",
  settings: "settings",
} as const;

export type WorkspaceId = (typeof WORKSPACE_IDS)[keyof typeof WORKSPACE_IDS];

type TranslateFn = (key: string, params?: Record<string, string | number>) => string;

const WORKSPACE_HREFS: Record<WorkspaceId, string> = {
  forecast: "/forecast",
  market: "/market",
  risk: "/risk",
  ai: "/ai",
  reports: "/reports",
  assets: "/assets",
  monitoring: "/monitoring",
  scenarios: "/scenarios",
  settings: "/settings",
};

const WORKSPACE_TAB_IDS: Record<WorkspaceId, string[]> = {
  forecast: ["overview", "weather", "accuracy", "history"],
  market: ["overview", "ptf", "smf", "trends"],
  risk: ["dashboard", "financial", "production", "timeline"],
  ai: ["pending", "archive"],
  reports: ["executive", "daily", "weekly", "portfolio", "export"],
  assets: ["plants", "turbines", "health", "performance"],
  monitoring: ["observability", "api", "health", "jobs", "logs", "activity"],
  scenarios: ["builder", "history"],
  settings: ["overview", "users", "models", "config", "language"],
};

export function buildWorkspaces(t: TranslateFn): Record<WorkspaceId, WorkspaceMeta> {
  return Object.fromEntries(
    (Object.keys(WORKSPACE_IDS) as WorkspaceId[]).map((id) => {
      const tabs = WORKSPACE_TAB_IDS[id].map((tabId) => ({
        id: tabId,
        label: t(`${id}.tabs.${tabId}`),
      }));
      return [
        id,
        {
          id,
          section: t(`${id}.section`),
          title: t(`${id}.title`),
          description: t(`${id}.description`),
          href: WORKSPACE_HREFS[id],
          tabs,
        },
      ];
    }),
  ) as Record<WorkspaceId, WorkspaceMeta>;
}

export function getWorkspaceTranslated(t: TranslateFn, workspaceId: WorkspaceId): WorkspaceMeta {
  return buildWorkspaces(t)[workspaceId];
}

/** @deprecated Use useWorkspaces() hook for translated labels */
export const WORKSPACES: Record<WorkspaceId, WorkspaceMeta> = {
  forecast: {
    id: "forecast",
    section: "Tahmin",
    title: "Tahmin Merkezi",
    description: "Üretim tahmini ve doğruluk",
    href: "/forecast",
    tabs: [
      { id: "overview", label: "Özet" },
      { id: "weather", label: "Hava" },
      { id: "accuracy", label: "Doğruluk" },
      { id: "history", label: "Geçmiş" },
    ],
  },
  market: {
    id: "market",
    section: "Piyasa",
    title: "Piyasa Analizi",
    description: "EPİAŞ PTF · SMF · trend",
    href: "/market",
    tabs: [
      { id: "overview", label: "Özet" },
      { id: "ptf", label: "PTF" },
      { id: "smf", label: "SMF" },
      { id: "trends", label: "Trendler" },
    ],
  },
  risk: {
    id: "risk",
    section: "Risk",
    title: "Risk Merkezi",
    description: "Risk değerlendirmesi ve izleme",
    href: "/risk",
    tabs: [
      { id: "dashboard", label: "Pano" },
      { id: "financial", label: "Finansal" },
      { id: "production", label: "Üretim" },
      { id: "timeline", label: "Zaman Çizelgesi" },
    ],
  },
  ai: {
    id: "ai",
    section: "Yapay Zeka",
    title: "AI Analiz",
    description: "Brifing · tavsiye · karar geçmişi",
    href: "/ai",
    tabs: [
      { id: "pending", label: "Bekleyen Aksiyonlar" },
      { id: "archive", label: "Arşiv" },
    ],
  },
  reports: {
    id: "reports",
    section: "Operasyon",
    title: "Raporlar",
    description: "Rapor üretimi ve dışa aktarma",
    href: "/reports",
    tabs: [
      { id: "executive", label: "Yönetici" },
      { id: "daily", label: "Günlük" },
      { id: "weekly", label: "Haftalık" },
      { id: "portfolio", label: "Portföy" },
      { id: "export", label: "Dışa Aktar" },
    ],
  },
  assets: {
    id: "assets",
    section: "Operasyon",
    title: "Varlıklar",
    description: "Santral envanteri",
    href: "/assets",
    tabs: [
      { id: "plants", label: "Santraller" },
      { id: "turbines", label: "Türbinler" },
      { id: "health", label: "Sağlık" },
      { id: "performance", label: "Performans" },
    ],
  },
  monitoring: {
    id: "monitoring",
    section: "Sistem",
    title: "İzleme",
    description: "API ve sistem sağlığı",
    href: "/monitoring",
    tabs: [
      { id: "observability", label: "Observability" },
      { id: "api", label: "API" },
      { id: "health", label: "Sağlık" },
      { id: "jobs", label: "İşler" },
      { id: "logs", label: "Loglar" },
      { id: "activity", label: "Akış" },
    ],
  },
  scenarios: {
    id: "scenarios",
    section: "Operasyon",
    title: "Senaryolar",
    description: "What-if simülasyonu",
    href: "/scenarios",
    tabs: [
      { id: "builder", label: "Oluşturucu" },
      { id: "history", label: "Geçmiş" },
    ],
  },
  settings: {
    id: "settings",
    section: "Sistem",
    title: "Yönetim",
    description: "Kullanıcılar · AI modelleri · yapılandırma",
    href: "/settings",
    tabs: [
      { id: "overview", label: "Genel" },
      { id: "users", label: "Kullanıcılar" },
      { id: "models", label: "AI Modelleri" },
      { id: "config", label: "Yapılandırma" },
      { id: "language", label: "Dil" },
    ],
  },
};

export const WORKSPACE_LIST: WorkspaceMeta[] = Object.values(WORKSPACES);
export const WORKSPACE_BY_HREF: Record<string, WorkspaceMeta> = Object.fromEntries(
  WORKSPACE_LIST.map((workspace) => [workspace.href, workspace]),
);

export function getWorkspaceTabs(workspaceId: WorkspaceId | string): WorkspaceTab[] {
  return WORKSPACES[workspaceId as WorkspaceId]?.tabs ?? [];
}

export function getDefaultTab(workspaceId: WorkspaceId | string): string {
  return WORKSPACES[workspaceId as WorkspaceId]?.tabs[0]?.id ?? "overview";
}

export function getWorkspace(workspaceId: WorkspaceId): WorkspaceMeta {
  return WORKSPACES[workspaceId];
}

export function resolveWorkspaceTab(workspace: WorkspaceMeta, tab: string | null | undefined): string {
  if (!tab) return workspace.tabs[0]?.id ?? "overview";
  return workspace.tabs.some((candidate) => candidate.id === tab)
    ? tab
    : (workspace.tabs[0]?.id ?? "overview");
}

export function getWorkspaceByPathname(pathname: string): WorkspaceMeta | null {
  const base = pathname.split("?")[0].split("#")[0];
  if (WORKSPACE_BY_HREF[base]) return WORKSPACE_BY_HREF[base];
  for (const workspace of WORKSPACE_LIST) {
    if (base.startsWith(`${workspace.href}/`)) return workspace;
  }
  return null;
}
