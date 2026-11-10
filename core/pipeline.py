"""Günlük olay akışı (Event Timeline) orkestratörü."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from core.config import get_settings
from core.data_quality import (
    enforce_pipeline_data_quality_gate,
    merge_quality_reports,
    run_pipeline_data_quality_gate,
    run_pre_pipeline_quality_gate,
)
from core.data_contracts import (
    CONTRACT_VERSION,
    validate_monitoring_contract,
    validate_prediction_contract,
    validate_recommendation_input_contract,
    validate_risk_input_contract,
)
from core.logger import get_logger
from core.rules import RuleEngine
from core.storage import PipelineStorage
from modules.alerting.service import AlertingService
from modules.ai.assistant import AIDecisionAssistant
from modules.ai.schemas import AIResponse
from modules.asset_registry.service import Asset, AssetRegistryService
from modules.ai.llm_health import llm_meta_from_ai_source
from modules.data_hub.source_telemetry import build_pipeline_telemetry
from modules.forecast.production.models.wind_model import WindPowerModel
from modules.forecast.production.schemas import ProductionForecastResponse
from modules.forecast.production.services import ProductionForecastService
from modules.performance.service import PerformanceMonitoringService
from modules.alerting.quality import evaluate_alert_quality
from modules.forecast.production.confidence_stack import build_confidence_stack
from modules.monitoring.drift import compute_drift_signals
from modules.monitoring.observability import build_pipeline_observability_snapshot
from modules.recommendation.causality import evaluate_decision_causality
from modules.recommendation.decision_reliability import (
    enforce_decision_reliability_gate,
    merge_decision_reliability_reports,
    run_decision_reliability_gate,
)
from modules.recommendation.quality import evaluate_recommendation_quality
from modules.risk.alerts import NotificationCenter
from modules.risk.schemas import DailyRiskScoreResponse
from modules.risk.scoring import RiskScoringService
from modules.forecast.production.model_reliability import (
    ModelReliabilityGateError,
    enforce_model_reliability_gate,
    merge_model_reliability_reports,
    run_model_reliability_gate,
)

STEP_DELAY_SECONDS = 0.3
_CUT_IN_SPEED = 3.0
_RATED_SPEED = 12.0


@dataclass
class PipelineRunResult:
    """Tek bir pipeline çalıştırmasının özeti."""

    target_date: date
    asset_id: str
    steps_completed: list[str] = field(default_factory=list)
    forecast: Optional[ProductionForecastResponse] = None
    performance: Optional[dict[str, Any]] = None
    risk: Optional[DailyRiskScoreResponse] = None
    metadata: dict[str, Any] = field(default_factory=dict)


def estimate_wind_speed_from_forecast_mw(forecast_mw: float, capacity_mw: float) -> float:
    """Power-curve ters modeli ile MW tahmininden yaklaşık rüzgar hızı (m/s).

    Yalnızca gerçek weather peak hızı yoksa fallback olarak kullanılır.
    """
    if forecast_mw <= 0 or capacity_mw <= 0:
        return 0.0
    if forecast_mw >= capacity_mw:
        return _RATED_SPEED + 3.0
    normalized = (forecast_mw / capacity_mw) ** (1 / 3)
    return _CUT_IN_SPEED + normalized * (_RATED_SPEED - _CUT_IN_SPEED)


def build_risk_data_dict(
    risk: DailyRiskScoreResponse,
    capacity_mw: float,
    *,
    wind_speed_mps: float | None = None,
) -> dict[str, Any]:
    """Risk sonucunu AI asistanı için sözlük formatına dönüştürür."""
    forecasts = [hour.forecast_mw for hour in risk.hours]
    ptfs = [hour.ptf_price for hour in risk.hours]
    max_forecast = max(forecasts) if forecasts else 0.0
    avg_forecast = sum(forecasts) / len(forecasts) if forecasts else 0.0
    avg_ptf = sum(ptfs) / len(ptfs) if ptfs else 0.0
    resolved_wind = (
        float(wind_speed_mps)
        if wind_speed_mps is not None
        else estimate_wind_speed_from_forecast_mw(max_forecast, capacity_mw)
    )

    return {
        "risk_score": risk.risk_score,
        "total_imbalance_cost_tl": risk.total_imbalance_cost_tl,
        "forecast_mw": max_forecast,
        "avg_forecast_mw": round(avg_forecast, 4),
        "avg_ptf_price": round(avg_ptf, 2),
        "wind_speed_mps": round(resolved_wind, 2),
    }


def _compute_drift_flags(
    current_mape: float,
    current_cost: float,
    recent_metrics: list[dict[str, Any]],
) -> dict[str, Any]:
    return compute_drift_signals(current_mape, current_cost, recent_metrics)


def _build_source_telemetry(
    forecast_source: str,
    scada_source: dict[str, Any],
    epias_source: str,
    *,
    weather_meta: dict[str, Any] | None = None,
    epias_meta: dict[str, Any] | None = None,
    llm_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return build_pipeline_telemetry(
        weather_source=forecast_source,
        weather_meta=weather_meta,
        scada_source=scada_source,
        epias_source=epias_source,
        epias_meta=epias_meta,
        llm_meta=llm_meta,
    )


class EventPipeline:
    """08:00–08:05 günlük operasyon zaman çizelgesi orkestratörü."""

    def __init__(
        self,
        asset_registry: Optional[AssetRegistryService] = None,
        ai_assistant: Optional[AIDecisionAssistant] = None,
        alerting_service: Optional[AlertingService] = None,
        storage: Optional[PipelineStorage] = None,
        performance_service: Optional[PerformanceMonitoringService] = None,
        rule_engine: Optional[RuleEngine] = None,
        notification_center: Optional[NotificationCenter] = None,
    ) -> None:
        self._asset_registry = asset_registry or AssetRegistryService()
        self._ai_assistant = ai_assistant or AIDecisionAssistant()
        self._alerting_service = alerting_service or AlertingService()
        self._storage = storage or PipelineStorage()
        self._performance_service = performance_service or PerformanceMonitoringService()
        self._rule_engine = rule_engine or RuleEngine()
        self._notification_center = notification_center or NotificationCenter()
        self._logger = get_logger("core.pipeline")
        self._current_asset: Optional[Asset] = None
        self._production_service: Optional[ProductionForecastService] = None
        self._risk_service: Optional[RiskScoringService] = None
        self._last_forecast: Optional[ProductionForecastResponse] = None
        self._last_performance: Optional[dict[str, Any]] = None
        self._last_risk: Optional[DailyRiskScoreResponse] = None
        self._last_ai_insight: Optional[str] = None
        self._last_action_plan: Optional[str] = None

    def _configure_for_asset(self, asset: Asset) -> None:
        """Seçilen santrale göre servisleri yapılandırır."""
        self._current_asset = asset
        self._production_service = ProductionForecastService(
            capacity_mw=asset.capacity_mw,
            asset_id=asset.id,
        )
        self._risk_service = RiskScoringService()

    def _audit_step(
        self,
        step: str,
        asset_id: str,
        target_date: date,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Pipeline adımını audit log'a yazar."""
        self._storage.log_step(
            step=step,
            asset_id=asset_id,
            target_date=target_date.isoformat(),
            status="completed",
            details=details or {},
        )

    def run_0800_forecast(self, target_date: date) -> ProductionForecastResponse:
        """08:00 — Üretim tahmini adımı."""
        if not self._current_asset or not self._production_service:
            raise RuntimeError("Asset yapılandırması eksik")

        asset = self._current_asset
        self._logger.info(
            "Forecast tetiklendi: asset_id=%s target_date=%s",
            asset.id,
            target_date,
        )
        forecast = self._production_service.forecast_daily_production(
            asset.lat,
            asset.lon,
            target_date,
        )
        self._last_forecast = forecast
        self._logger.info(
            "Forecast tamamlandi: asset_id=%s target_date=%s total_daily_mw=%s",
            asset.id,
            target_date,
            forecast.total_daily_mw,
        )
        return forecast

    def run_0801_performance_monitoring(
        self,
        forecast: ProductionForecastResponse,
        target_date: date,
    ) -> dict[str, Any]:
        """08:01 — Performans izleme ve sapma analizi."""
        asset_id = self._current_asset.id if self._current_asset else None
        self._logger.info(
            "Performans izleme basladi: asset_id=%s",
            asset_id,
        )
        performance = self._performance_service.evaluate_performance(
            forecast.model_dump(mode="json"),
            asset_id=asset_id,
            target_date=target_date.isoformat(),
        )
        self._last_performance = performance
        self._logger.info(
            "Performans izleme tamamlandi: asset_id=%s hours=%s",
            asset_id,
            len(performance.get("hours", [])),
        )
        return performance

    def run_0802_risk_calculation(
        self,
        target_date: date,
        performance_data: dict[str, Any],
    ) -> DailyRiskScoreResponse:
        """08:02 — Risk skoru hesaplama adımı."""
        if not self._current_asset or not self._risk_service:
            raise RuntimeError("Asset yapılandırması eksik")

        asset = self._current_asset
        self._logger.info(
            "Risk hesaplama basladi: asset_id=%s target_date=%s",
            asset.id,
            target_date,
        )
        risk = self._risk_service.calculate_daily_risk(target_date, performance_data)
        self._last_risk = risk
        self._logger.info(
            "Risk hesaplandı: asset_id=%s target_date=%s risk_score=%s total_cost=%s",
            asset.id,
            target_date,
            risk.risk_score,
            risk.total_imbalance_cost_tl,
        )
        return risk

    def run_0803_alert_generation(
        self,
        target_date: date,
        risk_data: dict[str, Any],
        performance_data: dict[str, Any],
        asset_id: str,
    ) -> dict[str, Any]:
        """08:03 — Risk ve performans tabanlı uyarı üretimi."""
        alert_status = self._alerting_service.evaluate_conditions_and_generate_alert(
            risk_data,
            performance_data,
            asset_id,
        )
        self._logger.info(
            "Alert kontrol edildi: asset_id=%s target_date=%s severity=%s message=%s",
            asset_id,
            target_date,
            alert_status.get("severity"),
            alert_status.get("message"),
        )
        return alert_status

    def run_0804_ai_explanation(self, target_date: date, risk_data: dict[str, Any]) -> AIResponse:
        """08:04 — Playbook veya LLM tabanlı AI açıklama üretimi."""
        ai_response = self._ai_assistant.generate_explanation(risk_data)
        self._last_ai_insight = ai_response.insight
        self._last_action_plan = ai_response.action_plan
        asset_id = self._current_asset.id if self._current_asset else None
        self._logger.info(
            "AI Assistant açıklaması üretildi: asset_id=%s target_date=%s action_plan=%s",
            asset_id,
            target_date,
            ai_response.action_plan,
        )
        return ai_response

    def run_0805_dashboard_update(
        self,
        target_date: date,
        metadata: dict[str, Any],
    ) -> None:
        """08:05 — Pipeline sonucunu depola ve arayüz için hazırla."""
        payload = {
            "target_date": target_date.isoformat(),
            **metadata,
        }
        self._storage.save_run(payload)
        asset_id = metadata.get("asset_id")
        self._logger.info(
            "Pipeline sonucu depolama alanına kaydedildi ve arayüz için hazır: "
            "asset_id=%s target_date=%s",
            asset_id,
            target_date,
        )

    def execute_daily_pipeline(
        self,
        asset_id: str,
        target_date: Optional[date] = None,
    ) -> PipelineRunResult:
        """Günlük 6 adımlık olay akışını seçilen santral için çalıştırır."""
        asset = self._asset_registry.get_asset_by_id(asset_id)
        self._configure_for_asset(asset)

        run_date = target_date or date.today()
        result = PipelineRunResult(target_date=run_date, asset_id=asset.id)
        pipeline_started = time.perf_counter()
        step_timings_ms: dict[str, float] = {}
        step_started = pipeline_started

        self._logger.info(
            "Gunluk pipeline basladi: asset_id=%s target_date=%s",
            asset.id,
            run_date,
        )

        pre_dq_report = enforce_pipeline_data_quality_gate(
            run_pre_pipeline_quality_gate(asset, run_date)
        )

        result.forecast = self.run_0800_forecast(run_date)
        validate_prediction_contract(result.forecast, asset_id=asset.id, target_date=run_date)
        forecast_model_report = enforce_model_reliability_gate(
            run_model_reliability_gate(
                model_info=self._production_service._wind_model.model_info,
            )
        )
        result.steps_completed.append("0800_forecast")
        step_timings_ms["0800_forecast"] = round((time.perf_counter() - step_started) * 1000, 2)
        step_started = time.perf_counter()
        self._audit_step(
            "0800_forecast",
            asset.id,
            run_date,
            {"total_daily_mw": result.forecast.total_daily_mw},
        )
        time.sleep(STEP_DELAY_SECONDS)

        result.performance = self.run_0801_performance_monitoring(result.forecast, run_date)
        validate_risk_input_contract(result.performance, asset_id=asset.id, target_date=run_date)
        result.steps_completed.append("0801_performance_monitoring")
        step_timings_ms["0801_performance_monitoring"] = round((time.perf_counter() - step_started) * 1000, 2)
        step_started = time.perf_counter()
        self._audit_step(
            "0801_performance_monitoring",
            asset.id,
            run_date,
            {"mape_percentage": result.performance.get("mape_percentage")},
        )
        time.sleep(STEP_DELAY_SECONDS)

        result.risk = self.run_0802_risk_calculation(run_date, result.performance)
        result.steps_completed.append("0802_risk_calculation")
        step_timings_ms["0802_risk_calculation"] = round((time.perf_counter() - step_started) * 1000, 2)
        step_started = time.perf_counter()
        self._audit_step(
            "0802_risk_calculation",
            asset.id,
            run_date,
            {
                "risk_score": result.risk.risk_score,
                "total_imbalance_cost_tl": result.risk.total_imbalance_cost_tl,
            },
        )
        time.sleep(STEP_DELAY_SECONDS)

        post_dq_report = enforce_pipeline_data_quality_gate(
            run_pipeline_data_quality_gate(
                asset=asset,
                target_date=run_date,
                forecast=result.forecast,
                performance=result.performance,
                risk=result.risk,
            )
        )
        dq_report = merge_quality_reports(pre_dq_report, post_dq_report)

        risk_data = (
            build_risk_data_dict(
                result.risk,
                asset.capacity_mw,
                wind_speed_mps=getattr(self._production_service, "_last_peak_wind_speed_mps", None),
            )
            if result.risk
            else {}
        )
        risk_data["asset_id"] = asset.id
        risk_data["mape_percentage"] = result.performance.get("mape_percentage", 0)
        validate_recommendation_input_contract(risk_data, target_date=run_date)
        alert_status = self.run_0803_alert_generation(
            run_date,
            risk_data,
            result.performance,
            asset.id,
        )
        result.steps_completed.append("0803_alert_generation")
        step_timings_ms["0803_alert_generation"] = round((time.perf_counter() - step_started) * 1000, 2)
        step_started = time.perf_counter()
        self._audit_step(
            "0803_alert_generation",
            asset.id,
            run_date,
            {"severity": alert_status.get("severity")},
        )
        time.sleep(STEP_DELAY_SECONDS)

        ai_response = self.run_0804_ai_explanation(run_date, risk_data)
        strict_playbook = get_settings().llm_provider == "mock"
        per_run_decision_report = enforce_decision_reliability_gate(
            run_decision_reliability_gate(
                risk_data=risk_data,
                risk_response=result.risk,
                ai_response=ai_response,
                model_attribution=result.forecast.attribution if result.forecast else None,
                model_info=self._production_service._wind_model.model_info,
                strict_playbook=strict_playbook,
            )
        )
        result.steps_completed.append("0804_ai_explanation")
        step_timings_ms["0804_ai_explanation"] = round((time.perf_counter() - step_started) * 1000, 2)
        step_started = time.perf_counter()
        self._audit_step(
            "0804_ai_explanation",
            asset.id,
            run_date,
            {"action_plan": ai_response.action_plan},
        )
        time.sleep(STEP_DELAY_SECONDS)

        triggered_rules = self._rule_engine.evaluate(
            {
                "risk_score": result.risk.risk_score if result.risk else 0,
                "mape_percentage": result.performance.get("mape_percentage", 0),
                "total_imbalance_cost_tl": (
                    result.risk.total_imbalance_cost_tl if result.risk else 0
                ),
                "ground_truth_mode": (
                    (result.performance.get("scada") or {}).get("mode")
                    if result.performance
                    else "unknown"
                ),
                "mape_informational": bool(
                    result.performance.get("mape_informational") if result.performance else False
                ),
                "evaluation_mode": (
                    result.performance.get("evaluation_mode") if result.performance else "production"
                ),
            }
        )
        notifications = self._notification_center.build_notifications(
            alert_status=alert_status,
            action_plan=ai_response.action_plan,
            risk_score=result.risk.risk_score if result.risk else 0,
        )

        result.metadata = {
            "asset_id": asset.id,
            "asset_name": asset.name,
            "asset_type": asset.type,
            "lat": asset.lat,
            "lon": asset.lon,
            "capacity_mw": asset.capacity_mw,
            "risk_score": result.risk.risk_score if result.risk else None,
            "total_imbalance_cost_tl": (
                result.risk.total_imbalance_cost_tl if result.risk else None
            ),
            "total_daily_mw": result.forecast.total_daily_mw if result.forecast else None,
            "weather_source": result.forecast.source if result.forecast else "unknown",
            "mape_percentage": (
                result.performance.get("mape_percentage") if result.performance else None
            ),
            "mape_informational": bool(
                result.performance.get("mape_informational") if result.performance else False
            ),
            "evaluation_mode": (
                result.performance.get("evaluation_mode") if result.performance else "production"
            ),
            "scada_source": result.performance.get("scada", {}) if result.performance else {},
            "epias_source": result.risk.market_source if result.risk else "unknown",
            "ai_insight": ai_response.insight,
            "action_plan": ai_response.action_plan,
            "ai_source": ai_response.source,
            "model_attribution": result.forecast.attribution if result.forecast else None,
            "alert_status": alert_status,
            "rules": triggered_rules,
            "notifications": notifications,
            "hours": [
                {
                    "timestamp": hour.timestamp.isoformat(),
                    "forecast_mw": hour.forecast_mw,
                    "actual_mw": hour.actual_mw,
                    "ptf_price": hour.ptf_price,
                    "imbalance_cost_tl": hour.imbalance_cost_tl,
                }
                for hour in result.risk.hours
            ]
            if result.risk
            else [],
            "data_contracts": {
                "version": CONTRACT_VERSION,
                "forecast_to_performance": "validated",
                "performance_to_risk": "validated",
                "risk_to_ai": "validated",
            },
            "data_quality": dq_report.to_dict(),
        }
        weather_meta = (
            self._production_service._weather_client.get_last_fetch_meta()
            if self._production_service
            else None
        )
        epias_meta = (
            self._risk_service._epias_client.get_last_fetch_meta()
            if self._risk_service
            else None
        )
        result.metadata["telemetry"] = _build_source_telemetry(
            forecast_source=result.metadata["weather_source"],
            scada_source=result.metadata["scada_source"],
            epias_source=result.metadata["epias_source"],
            weather_meta=weather_meta,
            epias_meta=epias_meta,
            llm_meta=llm_meta_from_ai_source(str(ai_response.source)),
        )

        current_mape = float(result.metadata.get("mape_percentage") or 0.0)
        current_cost = float(result.metadata.get("total_imbalance_cost_tl") or 0.0)
        recent_metrics = self._storage.get_recent_metrics(asset_id=asset.id, limit=30)
        drift = _compute_drift_flags(current_mape, current_cost, recent_metrics)
        result.metadata["drift"] = drift
        confidence_stack = build_confidence_stack(
            risk_score=int(result.risk.risk_score if result.risk else 0),
            mape_percentage=current_mape,
            drift=drift,
            hours=result.metadata.get("hours") or [],
        )
        result.metadata["confidence_stack"] = confidence_stack
        result.metadata["confidence_calibrated"] = confidence_stack["confidence_calibrated"]
        full_model_report = enforce_model_reliability_gate(
            run_model_reliability_gate(
                model_info=self._production_service._wind_model.model_info,
                confidence_stack=confidence_stack,
                drift=drift,
            )
        )
        result.metadata["model_reliability"] = merge_model_reliability_reports(
            forecast_model_report,
            full_model_report,
        ).to_dict()
        validate_monitoring_contract(result.metadata, target_date=run_date)
        result.metadata["data_contracts"]["pipeline_to_monitoring"] = "validated"

        self.run_0805_dashboard_update(run_date, result.metadata)
        result.steps_completed.append("0805_dashboard_update")
        step_timings_ms["0805_dashboard_update"] = round((time.perf_counter() - step_started) * 1000, 2)
        step_started = time.perf_counter()
        self._audit_step("0805_dashboard_update", asset.id, run_date, {"steps": len(result.steps_completed)})
        asset_runs = [
            run for run in self._storage.get_recent_runs(limit=30) if run.get("asset_id") == asset.id
        ]
        recommendation_quality = evaluate_recommendation_quality(asset_runs, period_days=7)
        alert_quality = evaluate_alert_quality(asset_runs, period_days=7)
        decision_causality = evaluate_decision_causality(asset_runs, period_days=7)
        result.metadata["recommendation_quality"] = recommendation_quality
        result.metadata["alert_quality"] = alert_quality
        result.metadata["decision_causality"] = decision_causality
        full_decision_report = enforce_decision_reliability_gate(
            run_decision_reliability_gate(
                risk_data=risk_data,
                risk_response=result.risk,
                ai_response=ai_response,
                model_attribution=result.forecast.attribution if result.forecast else None,
                model_info=self._production_service._wind_model.model_info,
                recommendation_quality=recommendation_quality,
                alert_quality=alert_quality,
                decision_causality=decision_causality,
                strict_playbook=strict_playbook,
            )
        )
        result.metadata["decision_reliability"] = merge_decision_reliability_reports(
            per_run_decision_report,
            full_decision_report,
        ).to_dict()
        step_timings_ms["pipeline_total_ms"] = round((time.perf_counter() - pipeline_started) * 1000, 2)
        result.metadata["observability"] = build_pipeline_observability_snapshot(
            step_timings_ms=step_timings_ms,
            telemetry=result.metadata.get("telemetry", {}),
            confidence_stack=confidence_stack,
            gates_passed={
                "data_quality": dq_report.gate_passed,
                "model_reliability": full_model_report.gate_passed,
                "decision_reliability": full_decision_report.gate_passed,
            },
        )
        self._storage.log_model_metrics(
            {
                "asset_id": asset.id,
                "target_date": run_date.isoformat(),
                "mape_percentage": current_mape,
                "risk_score": float(result.metadata.get("risk_score") or 0.0),
                "total_imbalance_cost_tl": current_cost,
                "drift": drift,
                "confidence_calibrated": result.metadata.get("confidence_calibrated"),
                "rules_count": len(triggered_rules),
                "telemetry": result.metadata.get("telemetry", {}),
                "data_quality": result.metadata.get("data_quality", {}),
                "recommendation_quality": recommendation_quality,
                "alert_quality": alert_quality,
                "confidence_stack": confidence_stack,
                "decision_causality": decision_causality,
                "model_reliability": result.metadata.get("model_reliability", {}),
                "decision_reliability": result.metadata.get("decision_reliability", {}),
                "observability": result.metadata.get("observability", {}),
            }
        )

        self._logger.info(
            "Gunluk pipeline tamamlandi: asset_id=%s target_date=%s steps=%s",
            asset.id,
            run_date,
            len(result.steps_completed),
        )
        return result
