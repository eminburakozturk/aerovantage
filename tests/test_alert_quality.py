"""Alert quality evaluation tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from modules.alerting.quality import (
    ALERT_QUALITY_VERSION,
    alert_fired,
    build_weekly_alert_report,
    evaluate_alert_quality,
    metrics_support_alert,
)


def _run(
    *,
    risk: float,
    mape: float,
    cost: float,
    severity: str = "WARNING",
    rules: list[dict] | None = None,
) -> dict:
    return {
        "asset_id": "RES-BAL-01",
        "risk_score": risk,
        "mape_percentage": mape,
        "total_imbalance_cost_tl": cost,
        "alert_status": {"severity": severity, "message": "test"},
        "rules": rules or [],
    }


def test_alert_fired_detects_warning_severity() -> None:
    assert alert_fired(_run(risk=30, mape=8, cost=1000, severity="WARNING")) is True
    assert alert_fired(_run(risk=30, mape=8, cost=1000, severity="INFO")) is False


def test_metrics_support_alert_uses_operational_thresholds() -> None:
    assert metrics_support_alert(_run(risk=60, mape=8, cost=1000)) is True
    assert metrics_support_alert(_run(risk=20, mape=18, cost=1000)) is True
    assert metrics_support_alert(_run(risk=20, mape=8, cost=6000)) is True
    assert metrics_support_alert(_run(risk=20, mape=8, cost=1000)) is False


def test_evaluate_alert_quality_precision_and_false_positive() -> None:
    runs = [
        _run(risk=70, mape=18, cost=60000, severity="WARNING"),
        _run(risk=72, mape=17, cost=62000, severity="WARNING"),
        _run(risk=25, mape=8, cost=1000, severity="WARNING"),
        _run(risk=20, mape=7, cost=900, severity="INFO"),
    ]
    result = evaluate_alert_quality(runs, period_days=7)

    assert result["alerts_fired"] == 3
    assert result["justified_alerts"] == 2
    assert result["precision_proxy"] == round(2 / 3, 4)
    assert result["false_positive_proxy"] >= 1
    assert result["false_positive_rate"] > 0
    assert "false_negative_rate" in result
    assert result["reportable"] is True
    assert result["version"] == ALERT_QUALITY_VERSION


def test_build_weekly_alert_report_includes_asset_id() -> None:
    report = build_weekly_alert_report("RES-BAL-01", storage=None, days=7)
    assert report["asset_id"] == "RES-BAL-01"
    assert "precision_proxy" in report


def test_monitoring_alert_quality_endpoint(auth_headers: dict[str, str]) -> None:
    client = TestClient(app)
    trigger = client.post(
        "/api/v1/pipeline/trigger-pipeline",
        json={"asset_id": "RES-BAL-01", "target_date": "2026-07-06"},
        headers=auth_headers,
    )
    assert trigger.status_code == 200, trigger.text

    response = client.get(
        "/api/v1/monitoring/alert-quality?asset_id=RES-BAL-01&days=7",
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["asset_id"] == "RES-BAL-01"
    assert data["version"] == ALERT_QUALITY_VERSION
    assert "precision_proxy" in data
    assert "false_positive_rate" in data
