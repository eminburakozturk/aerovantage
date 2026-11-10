import { API_BASE_URL, API_ROOT } from "./config";
import { apiFetch } from "./transport";
import type {
  AiHistoryEntry,
  AiModelsResponse,
  Asset,
  AuditEntry,
  ContextBriefingResponse,
  ExecutiveReportResponse,
  ExperimentBundleResponse,
  HealthResponse,
  JobEntry,
  LogEntry,
  AlertQualityResponse,
  ConfidenceStackResponse,
  DecisionCausalityResponse,
  DegradedSummaryResponse,
  DriftSummaryResponse,
  ObservabilitySummaryResponse,
  ModelAttributionResponse,
  ModelMetricEntry,
  ModelRegistryResponse,
  RecommendationQualityResponse,
  MarketPriceResponse,
  PipelineHistoryEntry,
  PipelineTriggerResponse,
  PlatformUser,
  PortfolioReportResponse,
  ScenarioRequest,
  ScenarioResult,
  SchedulerResponse,
  SystemConfigResponse,
  SystemKpiResponse,
  Turbine,
  WeatherForecastResponse,
  WeeklyReportResponse,
} from "./types";

export async function fetchAssets(): Promise<Asset[]> {
  return apiFetch<Asset[]>(`${API_BASE_URL}/assets`);
}

export async function fetchHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>(`${API_ROOT}/health`);
}

export async function fetchPipelineHistory(limit = 15, locale = "tr"): Promise<PipelineHistoryEntry[]> {
  return apiFetch<PipelineHistoryEntry[]>(
    `${API_BASE_URL}/pipeline/history?limit=${limit}&locale=${encodeURIComponent(locale)}`,
  );
}

export async function fetchSystemKpi(days = 30): Promise<SystemKpiResponse> {
  return apiFetch<SystemKpiResponse>(`${API_BASE_URL}/reporting/kpi?days=${days}`);
}

export async function triggerPipeline(
  assetId: string,
  targetDate?: string,
  locale = "tr",
): Promise<PipelineTriggerResponse> {
  return apiFetch<PipelineTriggerResponse>(
    `${API_BASE_URL}/pipeline/trigger-pipeline?locale=${encodeURIComponent(locale)}`,
    {
      method: "POST",
      body: JSON.stringify({
        asset_id: assetId,
        target_date: targetDate ?? new Date().toISOString().slice(0, 10),
      }),
    },
  );
}

export async function fetchExecutiveReport(
  assetId: string,
  days = 30,
  locale = "tr",
  reportType = "executive",
  workspace?: string | null,
): Promise<ExecutiveReportResponse> {
  const ws = workspace ? `&workspace=${encodeURIComponent(workspace)}` : "";
  return apiFetch<ExecutiveReportResponse>(
    `${API_BASE_URL}/reporting/executive?asset_id=${encodeURIComponent(assetId)}&days=${days}&locale=${encodeURIComponent(locale)}&report_type=${encodeURIComponent(reportType)}${ws}`,
  );
}

export async function askAboutReport(
  assetId: string,
  question: string,
  locale = "tr",
  reportType = "executive",
  days = 30,
): Promise<{ answer: string; citations: string[]; question: string }> {
  return apiFetch(
    `${API_BASE_URL}/reporting/ask`,
    {
      method: "POST",
      body: JSON.stringify({
        asset_id: assetId,
        question,
        locale,
        report_type: reportType,
        days,
      }),
    },
  );
}

export async function fetchPortfolioReport(
  assetIds: string[],
  days = 30,
  locale = "tr",
): Promise<PortfolioReportResponse> {
  return apiFetch<PortfolioReportResponse>(
    `${API_BASE_URL}/reporting/portfolio?asset_ids=${encodeURIComponent(assetIds.join(","))}&days=${days}&locale=${encodeURIComponent(locale)}`,
  );
}

export async function fetchTurbines(assetId: string): Promise<Turbine[]> {
  return apiFetch<Turbine[]>(`${API_BASE_URL}/assets/${encodeURIComponent(assetId)}/turbines`);
}

export async function fetchWeatherForecast(assetId: string, targetDate?: string): Promise<WeatherForecastResponse> {
  const qs = targetDate ? `&target_date=${targetDate}` : "";
  return apiFetch<WeatherForecastResponse>(
    `${API_BASE_URL}/weather/forecast?asset_id=${encodeURIComponent(assetId)}${qs}`,
  );
}

export async function fetchPtf(deliveryDate?: string): Promise<MarketPriceResponse> {
  const qs = deliveryDate ? `?delivery_date=${deliveryDate}` : "";
  return apiFetch<MarketPriceResponse>(`${API_BASE_URL}/market/ptf${qs}`);
}

export async function fetchSmf(deliveryDate?: string): Promise<MarketPriceResponse> {
  const qs = deliveryDate ? `?delivery_date=${deliveryDate}` : "";
  return apiFetch<MarketPriceResponse>(`${API_BASE_URL}/market/smf${qs}`);
}

export async function fetchWeeklyReport(assetId: string, weeks = 4, locale = "tr"): Promise<WeeklyReportResponse> {
  return apiFetch<WeeklyReportResponse>(
    `${API_BASE_URL}/reporting/weekly?asset_id=${encodeURIComponent(assetId)}&weeks=${weeks}&locale=${encodeURIComponent(locale)}`,
  );
}

export async function runScenario(body: ScenarioRequest, locale = "tr"): Promise<ScenarioResult> {
  return apiFetch<ScenarioResult>(
    `${API_BASE_URL}/scenarios/run?locale=${encodeURIComponent(locale)}`,
    {
      method: "POST",
      body: JSON.stringify(body),
    },
  );
}

export async function fetchScenarioHistory(limit = 20, locale = "tr"): Promise<ScenarioResult[]> {
  return apiFetch<ScenarioResult[]>(
    `${API_BASE_URL}/scenarios/history?limit=${limit}&locale=${encodeURIComponent(locale)}`,
  );
}

export async function fetchAuditTrail(limit = 50): Promise<AuditEntry[]> {
  return apiFetch<AuditEntry[]>(`${API_BASE_URL}/monitoring/audit?limit=${limit}`);
}

export async function fetchJobs(limit = 20): Promise<JobEntry[]> {
  return apiFetch<JobEntry[]>(`${API_BASE_URL}/monitoring/jobs?limit=${limit}`);
}

export async function fetchScheduler(locale = "tr"): Promise<SchedulerResponse> {
  return apiFetch<SchedulerResponse>(
    `${API_BASE_URL}/monitoring/scheduler?locale=${encodeURIComponent(locale)}`,
  );
}

export async function fetchLogs(limit = 100, locale = "tr"): Promise<LogEntry[]> {
  return apiFetch<LogEntry[]>(
    `${API_BASE_URL}/monitoring/logs?limit=${limit}&locale=${encodeURIComponent(locale)}`,
  );
}

export async function fetchModelMetrics(assetId?: string, limit = 50): Promise<ModelMetricEntry[]> {
  const assetPart = assetId ? `&asset_id=${encodeURIComponent(assetId)}` : "";
  return apiFetch<ModelMetricEntry[]>(`${API_BASE_URL}/monitoring/metrics?limit=${limit}${assetPart}`);
}

export async function fetchDegradedSummary(assetId?: string, limit = 200): Promise<DegradedSummaryResponse> {
  const assetPart = assetId ? `&asset_id=${encodeURIComponent(assetId)}` : "";
  return apiFetch<DegradedSummaryResponse>(
    `${API_BASE_URL}/monitoring/degraded-summary?limit=${limit}${assetPart}`,
  );
}

export async function fetchObservabilitySummary(
  assetId?: string,
  limit = 200,
): Promise<ObservabilitySummaryResponse> {
  const assetPart = assetId ? `&asset_id=${encodeURIComponent(assetId)}` : "";
  return apiFetch<ObservabilitySummaryResponse>(
    `${API_BASE_URL}/monitoring/observability-summary?limit=${limit}${assetPart}`,
  );
}

export async function fetchModelRegistry(
  assetId?: string,
  limit = 50,
): Promise<ModelRegistryResponse> {
  const assetPart = assetId ? `&asset_id=${encodeURIComponent(assetId)}` : "";
  return apiFetch<ModelRegistryResponse>(
    `${API_BASE_URL}/monitoring/model-registry?limit=${limit}${assetPart}`,
  );
}

export async function fetchExperimentBundle(experimentId: string): Promise<ExperimentBundleResponse> {
  return apiFetch<ExperimentBundleResponse>(
    `${API_BASE_URL}/monitoring/experiments/${encodeURIComponent(experimentId)}`,
  );
}

export async function fetchModelAttribution(assetId: string): Promise<ModelAttributionResponse> {
  return apiFetch<ModelAttributionResponse>(
    `${API_BASE_URL}/monitoring/model-attribution?asset_id=${encodeURIComponent(assetId)}`,
  );
}

export async function fetchDecisionCausality(
  assetId: string,
  days = 7,
): Promise<DecisionCausalityResponse> {
  return apiFetch<DecisionCausalityResponse>(
    `${API_BASE_URL}/monitoring/decision-causality?asset_id=${encodeURIComponent(assetId)}&days=${days}`,
  );
}

export async function fetchConfidenceStack(assetId: string): Promise<ConfidenceStackResponse> {
  return apiFetch<ConfidenceStackResponse>(
    `${API_BASE_URL}/monitoring/confidence-stack?asset_id=${encodeURIComponent(assetId)}`,
  );
}

export async function fetchAlertQuality(assetId: string, days = 7): Promise<AlertQualityResponse> {
  return apiFetch<AlertQualityResponse>(
    `${API_BASE_URL}/monitoring/alert-quality?asset_id=${encodeURIComponent(assetId)}&days=${days}`,
  );
}

export async function fetchDriftSummary(assetId?: string, limit = 200): Promise<DriftSummaryResponse> {
  const assetPart = assetId ? `&asset_id=${encodeURIComponent(assetId)}` : "";
  return apiFetch<DriftSummaryResponse>(
    `${API_BASE_URL}/monitoring/drift-summary?limit=${limit}${assetPart}`,
  );
}

export async function fetchRecommendationQuality(
  assetId: string,
  days = 7,
): Promise<RecommendationQualityResponse> {
  return apiFetch<RecommendationQualityResponse>(
    `${API_BASE_URL}/monitoring/recommendation-quality?asset_id=${encodeURIComponent(assetId)}&days=${days}`,
  );
}

export async function fetchAiHistory(limit = 20): Promise<AiHistoryEntry[]> {
  return apiFetch<AiHistoryEntry[]>(`${API_BASE_URL}/ai/history?limit=${limit}`);
}

export async function fetchAiModels(): Promise<AiModelsResponse> {
  return apiFetch<AiModelsResponse>(`${API_BASE_URL}/ai/models`);
}

export async function fetchContextBriefing(
  context: string,
  assetId: string,
  days = 7,
  locale = "tr",
): Promise<ContextBriefingResponse> {
  return apiFetch<ContextBriefingResponse>(
    `${API_BASE_URL}/ai/briefing?context=${encodeURIComponent(context)}&asset_id=${encodeURIComponent(assetId)}&days=${days}&locale=${encodeURIComponent(locale)}`,
  );
}

export async function fetchUsers(): Promise<PlatformUser[]> {
  return apiFetch<PlatformUser[]>(`${API_BASE_URL}/admin/users`);
}

export async function fetchSystemConfig(): Promise<SystemConfigResponse> {
  return apiFetch<SystemConfigResponse>(`${API_BASE_URL}/admin/config`);
}
