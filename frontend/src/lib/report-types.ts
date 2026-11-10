/** Report type helpers — R2 Adaptive Report Intelligence (existing Reports screen). */

export const REPORT_TYPES = [
  "executive",
  "operational",
  "forecast",
  "financial",
  "risk",
  "technical",
] as const;

export type ReportType = (typeof REPORT_TYPES)[number];

export const REPORT_TYPE_SECTIONS: Record<ReportType, string[]> = {
  executive: [
    "summary",
    "ai_brief",
    "scorecards",
    "financial",
    "forecast",
    "operational",
    "risk",
    "data",
    "model",
    "recommendations",
    "actions",
    "trends",
    "benchmark",
    "changes",
    "conclusion",
    "chat",
    "whatif",
  ],
  operational: [
    "summary",
    "ai_brief",
    "scorecards",
    "operational",
    "risk",
    "actions",
    "recommendations",
    "changes",
    "conclusion",
    "chat",
  ],
  forecast: [
    "summary",
    "ai_brief",
    "scorecards",
    "forecast",
    "model",
    "trends",
    "recommendations",
    "changes",
    "conclusion",
    "chat",
    "whatif",
  ],
  financial: [
    "summary",
    "ai_brief",
    "scorecards",
    "financial",
    "benchmark",
    "trends",
    "recommendations",
    "changes",
    "conclusion",
    "chat",
    "whatif",
  ],
  risk: [
    "summary",
    "ai_brief",
    "scorecards",
    "risk",
    "operational",
    "recommendations",
    "actions",
    "changes",
    "conclusion",
    "chat",
  ],
  technical: [
    "summary",
    "scorecards",
    "data",
    "model",
    "forecast",
    "trends",
    "changes",
    "conclusion",
    "chat",
  ],
};

const WORKSPACE_DEFAULT_REPORT: Record<string, ReportType> = {
  dashboard: "executive",
  reports: "executive",
  operations: "operational",
  monitoring: "operational",
  assets: "operational",
  forecast: "forecast",
  market: "financial",
  risk: "risk",
  ai: "technical",
  scenarios: "forecast",
  settings: "technical",
};

const LAST_WORKSPACE_KEY = "aerovantage.lastWorkspace";
const REPORT_TYPE_KEY = "aerovantage.reportType";

export function isReportType(value: string | null | undefined): value is ReportType {
  return !!value && (REPORT_TYPES as readonly string[]).includes(value);
}

export function normalizeReportType(value: string | null | undefined): ReportType {
  return isReportType(value) ? value : "executive";
}

export function suggestedReportType(workspace: string | null | undefined): ReportType {
  if (!workspace) return "executive";
  return WORKSPACE_DEFAULT_REPORT[workspace] ?? "executive";
}

export function rememberWorkspace(workspace: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(LAST_WORKSPACE_KEY, workspace);
  } catch {
    /* ignore */
  }
}

export function readLastWorkspace(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(LAST_WORKSPACE_KEY);
  } catch {
    return null;
  }
}

export function rememberReportType(type: ReportType): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(REPORT_TYPE_KEY, type);
  } catch {
    /* ignore */
  }
}

export function readStoredReportType(): ReportType | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(REPORT_TYPE_KEY);
    return isReportType(raw) ? raw : null;
  } catch {
    return null;
  }
}

/** Adaptive default: URL/type override > stored preference > workspace suggestion */
export function resolveInitialReportType(opts?: {
  urlType?: string | null;
  workspace?: string | null;
}): ReportType {
  if (isReportType(opts?.urlType)) return opts!.urlType!;
  const stored = readStoredReportType();
  if (stored) return stored;
  return suggestedReportType(opts?.workspace ?? readLastWorkspace());
}

export function sectionVisible(
  reportType: ReportType,
  section: string,
  apiSections?: string[],
  apiReportType?: string | null,
): boolean {
  // API sections only trusted when they match the selected type (avoid stale executive pack).
  if (apiSections?.length && apiReportType === reportType) {
    return apiSections.includes(section);
  }
  return REPORT_TYPE_SECTIONS[reportType].includes(section);
}

const SCORECARD_IDS_BY_TYPE: Record<ReportType, string[]> = {
  executive: ["overall", "financial", "operational", "forecast", "risk", "data", "model", "alerts"],
  operational: ["overall", "operational", "risk", "alerts", "forecast"],
  forecast: ["overall", "forecast", "model", "data", "alerts"],
  financial: ["overall", "financial", "forecast", "risk", "alerts"],
  risk: ["overall", "risk", "operational", "alerts", "financial"],
  technical: ["overall", "data", "model", "forecast", "alerts"],
};

export function filterScorecardsForType<T extends { id: string }>(reportType: ReportType, cards: T[]): T[] {
  const allowed = new Set(SCORECARD_IDS_BY_TYPE[reportType]);
  const filtered = cards.filter((c) => allowed.has(c.id));
  return filtered.length ? filtered : cards;
}
