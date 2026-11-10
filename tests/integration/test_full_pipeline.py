"""Tam zincir entegrasyon testi — Forecast → Reporting data contract."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app

EXPECTED_PIPELINE_STEPS = [
    "0800_forecast",
    "0801_performance_monitoring",
    "0802_risk_calculation",
    "0803_alert_generation",
    "0804_ai_explanation",
    "0805_dashboard_update",
]


def test_health_endpoint_is_public() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "data_hub" in body
    assert all(client_status.get("status") == "ok" for client_status in body["data_hub"].values())


def test_api_v1_requires_authentication() -> None:
    client = TestClient(app)
    endpoints = [
        ("GET", "/api/v1/assets", None),
        (
            "GET",
            "/api/v1/risk/daily",
            {"lat": 39.64, "lon": 27.88, "target_date": "2026-07-06"},
        ),
        ("POST", "/api/v1/pipeline/trigger-pipeline", None),
        ("GET", "/api/v1/reporting/executive", {"asset_id": "RES-BAL-01"}),
    ]
    for method, path, params in endpoints:
        if method == "GET":
            response = client.get(path, params=params)
        else:
            response = client.post(
                path,
                json={"asset_id": "RES-BAL-01", "target_date": "2026-07-06"},
            )
        assert response.status_code == 403, f"{method} {path} should return 403 without auth"


def test_full_pipeline_data_contract(auth_headers: dict[str, str]) -> None:
    """Forecast → Performance → Risk → Alert → AI → Reporting zincirini uçtan uca doğrular."""
    client = TestClient(app)
    asset_id = "RES-BAL-01"
    target_date = "2026-07-06"

    pipeline_response = client.post(
        "/api/v1/pipeline/trigger-pipeline",
        json={"asset_id": asset_id, "target_date": target_date},
        headers=auth_headers,
    )
    assert pipeline_response.status_code == 200, pipeline_response.text
    pipeline_data = pipeline_response.json()

    assert pipeline_data["asset_id"] == asset_id
    assert pipeline_data["steps_completed"] == EXPECTED_PIPELINE_STEPS

    metadata = pipeline_data["metadata"]

    # 08:00 Forecast → saatlik üretim tahmini
    hours = metadata["hours"]
    assert len(hours) == 24
    assert all("forecast_mw" in hour for hour in hours)

    # 08:01 Performance → gerçekleşen ve MAPE
    assert all("actual_mw" in hour for hour in hours)
    assert metadata["mape_percentage"] is not None
    assert float(metadata["mape_percentage"]) >= 0

    # 08:02 Risk → maliyet ve skor
    assert metadata["risk_score"] is not None
    assert int(metadata["risk_score"]) >= 0
    assert metadata["total_imbalance_cost_tl"] is not None
    assert float(metadata["total_imbalance_cost_tl"]) >= 0
    assert all("imbalance_cost_tl" in hour for hour in hours)

    # 08:03 Alert
    alert_status = metadata["alert_status"]
    assert alert_status["severity"] in {"INFO", "WARNING", "CRITICAL"}
    assert alert_status["message"]

    # 08:04 AI
    assert metadata["ai_insight"]
    assert metadata["action_plan"]
    assert metadata.get("notifications")
    assert metadata.get("rules")

    # Performance → Risk data contract: forecast/actual tutarlılığı
    for hour in hours:
        assert hour["forecast_mw"] >= 0
        assert hour["actual_mw"] >= 0

    # Reporting — pipeline kaydından executive rapor
    report_response = client.get(
        "/api/v1/reporting/executive",
        params={"asset_id": asset_id, "days": 30},
        headers=auth_headers,
    )
    assert report_response.status_code == 200, report_response.text
    report = report_response.json()

    assert report["asset_id"] == asset_id
    assert report["period_days"] == 30
    assert report["total_imbalance_cost_tl"] >= float(metadata["total_imbalance_cost_tl"])
    assert report["average_mape"] >= 0
    assert report["critical_alerts_count"] >= 0
    assert report["executive_summary"]
