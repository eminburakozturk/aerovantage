import {
  fetchExecutiveReport,
  fetchPipelineHistory,
  fetchPortfolioReport,
  triggerPipeline,
} from "./endpoints";
import type {
  DashboardData,
  ExecutiveReportResponse,
  PipelineHistoryEntry,
  PipelineMetadata,
  PipelineTriggerResponse,
  PortfolioReportResponse,
} from "./types";

function pickLatestForAsset(
  history: PipelineHistoryEntry[],
  assetId: string,
): PipelineHistoryEntry | undefined {
  return history.find((entry) => entry.asset_id === assetId) ?? history[0];
}

function buildDashboardFromSources(
  assetId: string,
  executive: ExecutiveReportResponse,
  portfolio: PortfolioReportResponse | null,
  historyEntry: PipelineHistoryEntry | undefined,
  pipeline: PipelineTriggerResponse | null,
): DashboardData {
  const meta: PipelineMetadata | PipelineHistoryEntry | undefined = pipeline?.metadata ?? historyEntry;
  const usePortfolio = portfolio != null && portfolio.asset_ids.includes(assetId);

  return {
    assetId,
    assetName: meta?.asset_name ?? assetId,
    targetDate: pipeline?.target_date ?? historyEntry?.target_date ?? new Date().toISOString().slice(0, 10),
    riskScore: Number(meta?.risk_score ?? 0),
    liveMapePercentage: Number(meta?.mape_percentage ?? executive.average_mape),
    // Seçili santral KPI'ları her zaman executive (asset) — portföy toplamı karışmasın
    totalImbalanceCostTl: executive.total_imbalance_cost_tl,
    averageMape: executive.average_mape,
    executiveSummary: executive.executive_summary,
    forecastMw: Number(meta?.total_daily_mw ?? 0),
    aiInsight: meta?.ai_insight ?? historyEntry?.ai_insight ?? executive.executive_summary,
    actionPlan: meta?.action_plan ?? historyEntry?.action_plan ?? "",
    criticalAlertsCount: executive.critical_alerts_count,
    notifications: meta?.notifications ?? historyEntry?.notifications ?? [],
    rules: meta?.rules ?? historyEntry?.rules ?? [],
    stepsCompleted: pipeline?.steps_completed ?? [],
    hourlyProduction: meta?.hours ?? historyEntry?.hours ?? [],
    kpiSource: "executive",
    portfolioAssetIds: portfolio?.asset_ids ?? [assetId],
    portfolioTotalCostTl: usePortfolio ? portfolio.total_cost : undefined,
  };
}

export async function fetchLiveDashboard(
  assetId: string,
  portfolioAssetIds: string[],
  days = 30,
  locale = "tr",
): Promise<DashboardData> {
  const [executive, history] = await Promise.all([
    fetchExecutiveReport(assetId, days, locale),
    fetchPipelineHistory(20, locale),
  ]);

  let portfolio: PortfolioReportResponse | null = null;
  if (portfolioAssetIds.length >= 2) {
    try {
      portfolio = await fetchPortfolioReport(portfolioAssetIds, days, locale);
    } catch {
      portfolio = null;
    }
  }

  const latest = pickLatestForAsset(history, assetId);
  return buildDashboardFromSources(assetId, executive, portfolio, latest, null);
}

export async function fetchDashboardWithPipeline(
  assetId: string,
  portfolioAssetIds: string[],
  days = 30,
  locale = "tr",
): Promise<DashboardData> {
  const pipeline = await triggerPipeline(assetId, undefined, locale);
  const [executive, history] = await Promise.all([
    fetchExecutiveReport(assetId, days, locale),
    fetchPipelineHistory(20, locale),
  ]);

  let portfolio: PortfolioReportResponse | null = null;
  if (portfolioAssetIds.length >= 2) {
    try {
      portfolio = await fetchPortfolioReport(portfolioAssetIds, days, locale);
    } catch {
      portfolio = null;
    }
  }

  const latest = pickLatestForAsset(history, assetId);
  return buildDashboardFromSources(assetId, executive, portfolio, latest, pipeline);
}

/** @deprecated fetchLiveDashboard veya fetchDashboardWithPipeline kullanın */
export async function fetchDashboardData(assetId: string, days = 30, locale = "tr"): Promise<DashboardData> {
  return fetchDashboardWithPipeline(assetId, [assetId], days, locale);
}
