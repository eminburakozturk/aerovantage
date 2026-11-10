"""Belge 6 mimari ayrıştırma testi — Performance / Risk / Pipeline zinciri."""

from __future__ import annotations

from datetime import date

from core.pipeline import EventPipeline
from fastapi.testclient import TestClient

from api.main import app
from modules.performance.service import PerformanceMonitoringService
from modules.risk.scoring import RiskScoringService


def test_performance_service_returns_deviation() -> None:
    service = PerformanceMonitoringService()
    forecast_data = {
        "hours": [
            {
                "timestamp": "2026-07-06T08:00:00",
                "generated_mw": 10.0,
            }
        ]
    }
    result = service.evaluate_performance(forecast_data)
    hour = result["hours"][0]
    assert hour["forecast_mw"] == 10.0
    assert hour["actual_mw"] >= 0
    assert hour["deviation_mw"] == round(hour["actual_mw"] - 10.0, 4)
    assert "mape_percentage" in hour


def test_performance_includes_daily_mape() -> None:
    service = PerformanceMonitoringService()
    result = service.evaluate_performance(
        {
            "hours": [
                {"timestamp": "2026-07-06T08:00:00", "generated_mw": 10.0},
                {"timestamp": "2026-07-06T09:00:00", "generated_mw": 12.0},
            ]
        }
    )
    assert "mape_percentage" in result
    assert result["mape_percentage"] >= 0


def test_risk_uses_external_deviation_only() -> None:
    risk = RiskScoringService()
    performance_data = {
        "hours": [
            {
                "timestamp": "2026-07-06T12:00:00",
                "forecast_mw": 20.0,
                "actual_mw": 18.0,
                "deviation_mw": -2.0,
                "mape_percentage": 11.11,
            }
        ]
    }
    result = risk.calculate_daily_risk(date(2026, 7, 6), performance_data)
    assert result.hours[0].forecast_mw == 20.0
    assert result.hours[0].actual_mw == 18.0
    assert result.risk_score >= 0


def test_pipeline_six_step_chain() -> None:
    pipeline = EventPipeline()
    result = pipeline.execute_daily_pipeline("RES-BAL-01", date(2026, 7, 6))
    assert result.steps_completed == [
        "0800_forecast",
        "0801_performance_monitoring",
        "0802_risk_calculation",
        "0803_alert_generation",
        "0804_ai_explanation",
        "0805_dashboard_update",
    ]
    assert result.performance is not None
    assert result.risk is not None
    assert len(result.performance["hours"]) == len(result.risk.hours) == 24
    assert "telemetry" in result.metadata
    assert "is_degraded" in result.metadata["telemetry"]


def test_api_trigger_pipeline(auth_headers: dict[str, str]) -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/pipeline/trigger-pipeline",
        json={"asset_id": "RES-BAL-01", "target_date": "2026-07-06"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data["steps_completed"]) == 6
    assert data["steps_completed"][-1] == "0805_dashboard_update"
    assert "mape_percentage" in data["metadata"]
    assert "telemetry" in data["metadata"]


def test_monitoring_degraded_summary_endpoint(auth_headers: dict[str, str]) -> None:
    client = TestClient(app)
    trigger = client.post(
        "/api/v1/pipeline/trigger-pipeline",
        json={"asset_id": "RES-BAL-01", "target_date": "2026-07-06"},
        headers=auth_headers,
    )
    assert trigger.status_code == 200, trigger.text
    response = client.get("/api/v1/monitoring/degraded-summary?limit=20", headers=auth_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert "degraded_ratio_pct" in data
    assert "source_mode_counts" in data


if __name__ == "__main__":
    test_performance_service_returns_deviation()
    test_risk_uses_external_deviation_only()
    test_pipeline_six_step_chain()
    test_api_trigger_pipeline()
    print("ALL_ARCHITECTURE_TESTS_PASSED")
