export interface Asset {
  id: string;
  name: string;
  type: string;
  lat: number;
  lon: number;
  capacity_mw: number;
}

export interface NotificationItem {
  level: string;
  title: string;
  message: string;
}

export interface RuleItem {
  rule_id: string;
  severity: string;
  message: string;
  action: string;
}

export interface HourlyProductionPoint {
  timestamp: string;
  forecast_mw: number;
  actual_mw: number;
  ptf_price?: number;
  imbalance_cost_tl?: number;
}

export interface PipelineTriggerResponse {
  status: string;
  asset_id: string;
  target_date: string;
  steps_completed: string[];
  metadata: PipelineMetadata;
}

export interface PipelineMetadata {
  asset_id: string;
  asset_name?: string;
  risk_score?: number;
  mape_percentage?: number;
  total_daily_mw?: number;
  total_imbalance_cost_tl?: number;
  ai_insight?: string;
  action_plan?: string;
  alert_status?: { severity?: string; message?: string };
  notifications?: NotificationItem[];
  rules?: RuleItem[];
  hours?: HourlyProductionPoint[];
}

export interface ReportScorecard {
  id: string;
  label: string;
  value: string;
  level: string;
  level_label?: string;
  note?: string;
}

export interface ReportAiBrief {
  title?: string;
  status_summary?: string;
  top_event?: string;
  top_risk?: string;
  financial_impact?: string;
  operational_impact?: string;
  recommended_action?: string;
  confidence?: number;
  simulation?: boolean;
  focus?: string;
}

export interface ReportActionItem {
  id?: string;
  title?: string;
  priority?: string;
  priority_label?: string;
  status?: string;
  owner?: string;
  expected_impact?: string;
}

export interface ReportRecommendation {
  title?: string;
  situation?: string;
  impact?: string;
  priority?: string;
  priority_label?: string;
  confidence?: number;
}

export interface ExecutiveReportResponse {
  report_id: string;
  generated_at: string;
  asset_id: string;
  period_days: number;
  total_imbalance_cost_tl: number;
  average_mape: number;
  critical_alerts_count: number;
  executive_summary: string;
  run_count?: number;
  scorecards?: ReportScorecard[];
  ai_brief?: ReportAiBrief;
  financial?: Record<string, unknown>;
  forecast?: Record<string, unknown>;
  operational?: Record<string, unknown>;
  risk?: Record<string, unknown>;
  data_intelligence?: Record<string, unknown>;
  model_intelligence?: Record<string, unknown>;
  recommendations?: ReportRecommendation[];
  actions?: ReportActionItem[];
  trends?: {
    period_days?: number;
    points?: Array<Record<string, unknown>>;
    cost_sparkline?: number[];
    mape_sparkline?: number[];
    risk_sparkline?: number[];
  };
  benchmark?: Record<string, unknown>;
  conclusion?: string;
  mape_informational?: boolean;
  report_type?: string;
  changes_since_last?: {
    summary?: string;
    kpi_up?: string[];
    kpi_down?: string[];
    new_alerts?: number;
    closed_alerts?: number;
    cost_delta_pct?: number;
    mape_delta?: number;
    risk_delta?: number;
  };
  visible_sections?: string[];
  adaptive_hint?: string;
}

export interface PortfolioReportResponse {
  report_id: string;
  generated_at: string;
  asset_ids: string[];
  period_days: number;
  total_cost: number;
  avg_mape: number;
  critical_alert_count: number;
  summary: string;
  assets: ExecutiveReportResponse[];
}

export interface SystemKpiResponse {
  period_days: number;
  average_mape: number;
  uptime_percentage: number;
  api_availability_percentage: number;
  pipeline_run_count: number;
  data_hub: Record<
    string,
    {
      status: string;
      client?: string;
      mode?: string;
      source?: string;
      confidence?: string;
      live?: string;
      label?: string;
      provider?: string;
    }
  >;
}

export interface HealthResponse {
  status: string;
  data_hub: Record<
    string,
    {
      status: string;
      client?: string;
      mode?: string;
      source?: string;
      confidence?: string;
      live?: string;
      label?: string;
      provider?: string;
    }
  >;
}

export interface PipelineHistoryEntry {
  saved_at?: string;
  target_date?: string;
  asset_id?: string;
  asset_name?: string;
  risk_score?: number;
  mape_percentage?: number;
  total_daily_mw?: number;
  total_imbalance_cost_tl?: number;
  ai_insight?: string;
  action_plan?: string;
  alert_status?: { severity?: string; message?: string };
  notifications?: NotificationItem[];
  rules?: RuleItem[];
  hours?: HourlyProductionPoint[];
}

export interface DashboardData {
  assetId: string;
  assetName: string;
  targetDate: string;
  riskScore: number;
  liveMapePercentage: number;
  totalImbalanceCostTl: number;
  averageMape: number;
  executiveSummary: string;
  forecastMw: number;
  aiInsight: string;
  actionPlan: string;
  criticalAlertsCount: number;
  notifications: NotificationItem[];
  rules: RuleItem[];
  stepsCompleted: string[];
  hourlyProduction: HourlyProductionPoint[];
  kpiSource: "executive" | "portfolio";
  portfolioAssetIds: string[];
  /** Portföy toplam maliyeti (opsiyonel; KPI'da kullanılmaz) */
  portfolioTotalCostTl?: number;
}

export interface Turbine {
  id: string;
  model: string;
  capacity_mw: number;
  status: string;
  health_score: number;
}

export interface WeatherHour {
  timestamp: string;
  temperature: number;
  wind_speed: number;
  wind_direction: number;
  air_pressure: number;
}

export interface WeatherForecastResponse {
  asset_id: string;
  asset_name: string;
  latitude: number;
  longitude: number;
  target_date: string;
  hours: WeatherHour[];
  source: string;
}

export interface MarketPriceHour {
  hour: number;
  ptf?: number;
  smf?: number;
}

export interface MarketPriceResponse {
  delivery_date: string;
  hours: MarketPriceHour[];
  source: string;
}

export interface WeeklyReportResponse {
  asset_id: string;
  weeks_analyzed: number;
  weeks: Array<{
    week: string;
    runs: number;
    total_cost_tl: number;
    average_mape: number;
    max_risk_score: number;
  }>;
  summary: string;
}

export interface ScenarioRequest {
  asset_id: string;
  target_date?: string;
  wind_adjustment_pct?: number;
  ptf_adjustment_pct?: number;
  turbines_down?: number;
}

export interface ScenarioResult {
  scenario_id: string;
  generated_at: string;
  asset_id: string;
  target_date: string;
  baseline_forecast_mw: number;
  adjusted_forecast_mw: number;
  baseline_cost_tl: number;
  adjusted_cost_tl: number;
  baseline_risk_score: number;
  adjusted_risk_score: number;
  capacity_impact_mw: number;
  summary: string;
}

export interface AuditEntry {
  audit_id: string;
  step: string;
  asset_id: string;
  target_date: string;
  status: string;
  recorded_at: string;
}

export interface JobEntry {
  job_id: string;
  type: string;
  asset_id?: string;
  target_date?: string;
  status: string;
}

export interface SchedulerResponse {
  timezone: string;
  jobs: Array<{
    id: string;
    name: string;
    schedule: string;
    status: string;
    last_run?: string;
    next_run?: string;
  }>;
}

export interface LogEntry {
  timestamp: string;
  level: string;
  source?: string;
  message: string;
}

export interface ModelMetricEntry {
  recorded_at: string;
  asset_id: string;
  target_date: string;
  mape_percentage: number;
  risk_score: number;
  total_imbalance_cost_tl: number;
  confidence_calibrated?: number;
  rules_count?: number;
  drift?: {
    version?: string;
    has_baseline?: boolean;
    detection_method?: string;
    mape_drift?: boolean;
    cost_drift?: boolean;
    mape_delta?: number;
    cost_delta?: number;
    residual_mape?: number;
    residual_cost?: number;
    mape_z_score?: number;
    cost_z_score?: number;
    drift_severity?: string;
    baseline_mape?: number;
    baseline_cost?: number;
  };
  telemetry?: {
    is_degraded?: boolean;
    degraded_sources?: string[];
    sources?: {
      weather?: { source?: string; mode?: string };
      scada?: {
        mode?: string;
        reason?: string;
        source?: string;
        confidence?: string;
        live?: string | boolean;
        label?: string;
        provider?: string;
      };
      epias?: { source?: string; mode?: string };
    };
  };
  recommendation_quality?: {
    quality_score?: number;
    reportable?: boolean;
    action_coverage?: number;
    improved_after_action_ratio?: number;
  };
}

export interface DegradedSummaryResponse {
  version?: string;
  sample_size: number;
  degraded_runs: number;
  degraded_ratio_pct: number;
  avg_mock_usage_rate?: number;
  source_mode_counts: {
    weather: { mock: number; live: number; simulated?: number; fallback?: number };
    scada: { mock: number; live: number; simulated?: number; fallback?: number };
    epias: { mock: number; live: number; simulated?: number; fallback?: number };
    gemini?: { mock: number; live: number; simulated?: number; fallback?: number };
  };
  degraded_reason_counts: Record<string, number>;
}

export interface ObservabilitySummaryResponse {
  version: string;
  sample_size: number;
  fallback_reasons: Record<string, number>;
  degraded_ratio_pct: number;
  avg_mock_usage_rate: number;
  source_success_rates: Record<string, number>;
  api_success: {
    pipeline_runs: number;
    successful_runs: number;
    success_rate: number;
    expected_steps: number;
  };
  latency: {
    sample_size: number;
    avg_pipeline_total_ms: number;
    avg_step_timings_ms: Record<string, number>;
  };
  coverage: {
    version: string;
    sample_size: number;
    avg_coverage_rate: number;
    meets_target_runs: number;
    meets_target_ratio: number;
  };
  endpoints: Record<string, boolean>;
  asset_id?: string;
}

export interface ModelRegistryEntry {
  registry_version: string;
  experiment_id: string;
  asset_id: string;
  model_type: string;
  feature_schema_version?: string;
  feature_names: string[];
  trained_samples: number;
  dataset_source: string;
  dataset_runs: number;
  hyperparameters: Record<string, number>;
  git_commit: string;
  artifact_path?: string;
  train_mae?: number;
  val_mae?: number;
  deployable?: boolean;
  created_at: string;
}

export interface ModelRegistryResponse {
  version: string;
  count: number;
  entries: ModelRegistryEntry[];
}

export interface ExperimentBundleResponse {
  found: boolean;
  experiment_id?: string;
  experiment?: Record<string, unknown>;
  metrics?: Record<string, unknown>;
  model?: Record<string, unknown>;
}

export interface ModelAttributionResponse {
  asset_id: string;
  target_date?: string;
  found: boolean;
  version: string;
  method?: string;
  prediction_mw?: number;
  features: Array<{
    feature: string;
    shap_value?: number;
    weight: number;
  }>;
}

export interface DecisionCausalityResponse {
  asset_id: string;
  version: string;
  period_days: number;
  samples: number;
  action_pairs: number;
  control_pairs: number;
  avg_improvement_with_action: number;
  avg_improvement_without_action: number;
  causality_lift: number;
  causality_signal: string;
  reportable: boolean;
  generated_at: string;
}

export interface ConfidenceStackResponse {
  asset_id: string;
  target_date?: string;
  found: boolean;
  version: string;
  base_confidence?: number;
  confidence_calibrated?: number;
  prediction_interval?: {
    point_mw: number;
    lower_mw: number;
    upper_mw: number;
    margin_mw: number;
    margin_pct: number;
  };
  coverage?: {
    covered_hours: number;
    evaluated_hours: number;
    coverage_rate: number;
    target_coverage: number;
    meets_target: boolean;
  };
}

export interface AlertQualityResponse {
  asset_id: string;
  version: string;
  period_days: number;
  samples: number;
  alerts_fired: number;
  justified_alerts: number;
  precision_proxy: number;
  false_positive_proxy: number;
  false_positive_rate: number;
  outcome_confirmed_rate: number;
  quality_score: number;
  reportable: boolean;
  generated_at: string;
}

export interface DriftSummaryResponse {
  version: string;
  sample_size: number;
  mape_drift_runs: number;
  cost_drift_runs: number;
  z_score_detections: number;
  legacy_detections: number;
  severity_counts: {
    normal: number;
    warn: number;
    crit: number;
  };
}

export interface RecommendationQualityResponse {
  asset_id: string;
  version: string;
  period_days: number;
  samples: number;
  evaluated_actions: number;
  action_coverage: number;
  improved_after_action_ratio: number;
  cost_improved_after_action_ratio: number;
  mape_improved_after_action_ratio: number;
  quality_score: number;
  reportable: boolean;
  generated_at: string;
}

export interface AiHistoryEntry {
  recorded_at: string;
  source: string;
  asset_id?: string;
  risk_score?: number;
  insight: string;
  action_plan: string;
}

export interface AiModelsResponse {
  active_provider: string;
  active_model: { name: string; version: string; type: string };
  available_providers: string[];
  api_key_configured: boolean;
  playbook_entries?: number;
  mode?: "live" | "playbook";
  readiness?: string;
  live_ready?: boolean;
  cutover_hint?: string;
}

export interface ContextBriefingStructured {
  title: string;
  status_summary: string;
  analysis: string;
  risk: string;
  financial_impact: string;
  operational_impact: string;
  recommended_action: string;
  alternative_action: string;
  confidence: number;
}

export interface ContextBriefingTechnical {
  model: string;
  confidence: number;
  feature_importance: Array<{ feature: string; weight: number }>;
  forecast_quality: string;
  data_quality: string;
}

export interface ContextBriefingDecision {
  at: string;
  insight: string;
  action: string;
}

export interface BriefingAnnotation {
  id: string;
  target_type: "decision" | "alert" | "recommendation" | "kpi" | string;
  target_id: string;
  label: string;
  insight: string;
  severity: string;
  confidence: number;
  recommended_action: string;
  context: string;
}

export interface ContextBriefingResponse {
  context: string;
  asset_id: string;
  asset_name: string;
  mode?: "executive" | "technical";
  expert?: {
    id: string;
    title: string;
    subtitle: string;
  };
  structured?: ContextBriefingStructured;
  panel?: {
    executive_summary: string;
    top_risk: string;
    top_recommendation: string;
    financial_impact: string;
    confidence: number;
    contribution_summary?: Array<{ feature: string; weight: number }>;
  };
  technical?: ContextBriefingTechnical;
  recent_decisions?: ContextBriefingDecision[];
  executive_summary: string;
  technical_detail: string;
  recommendations: string[];
  annotations?: BriefingAnnotation[];
  metrics: {
    risk_score: number;
    mape_percentage: number;
    live_mape_percentage?: number;
    period_mape_percentage?: number;
    total_imbalance_cost_tl: number;
    confidence?: number;
    drift?: {
      has_baseline?: boolean;
      mape_drift?: boolean;
      cost_drift?: boolean;
      mape_delta?: number;
      cost_delta?: number;
      baseline_mape?: number;
      baseline_cost?: number;
    };
  };
  recommendation_quality?: {
    version?: string;
    period_days?: number;
    samples: number;
    action_coverage: number;
    improved_after_action_ratio: number;
    cost_improved_after_action_ratio?: number;
    mape_improved_after_action_ratio?: number;
    quality_score?: number;
    reportable?: boolean;
    evaluated_actions?: number;
    generated_at?: string;
  };
  ai_source?: string;
  ai_connected?: boolean;
}

export interface PlatformUser {
  id: string;
  name: string;
  email: string;
  role: string;
  status: string;
}

export interface SystemConfigResponse {
  app_name: string;
  app_env: string;
  log_level: string;
  epias_use_mock: boolean;
  weather_use_mock: boolean;
  scada_use_mock: boolean;
  llm_provider: string;
  llm_api_key_configured: boolean;
}
