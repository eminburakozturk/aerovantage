"""Statistical drift detection tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from modules.monitoring.drift import (
    DRIFT_DETECTION_VERSION,
    compute_drift_signals,
    summarize_drift_metrics,
)


def _metric(mape: float, cost: float) -> dict:
    return {"mape_percentage": mape, "total_imbalance_cost_tl": cost}


def test_compute_drift_signals_uses_z_score_with_enough_samples() -> None:
    baseline = [
        _metric(10.0, 30000.0),
        _metric(10.2, 31000.0),
        _metric(9.8, 29000.0),
        _metric(10.1, 30500.0),
        _metric(9.9, 29500.0),
        _metric(10.0, 30000.0),
    ]
    result = compute_drift_signals(18.0, 90000.0, baseline)

    assert result["detection_method"] == "z_score"
    assert result["mape_drift"] is True
    assert result["cost_drift"] is True
    assert result["residual_mape"] > 0
    assert result["mape_z_score"] >= 2.0
    assert result["version"] == DRIFT_DETECTION_VERSION


def test_compute_drift_signals_falls_back_to_legacy_threshold() -> None:
    baseline = [_metric(10.0, 30000.0), _metric(10.5, 31000.0)]
    result = compute_drift_signals(14.0, 60000.0, baseline)

    assert result["detection_method"] == "legacy_threshold"
    assert result["mape_drift"] is True
    assert result["cost_drift"] is True


def test_compute_drift_signals_without_baseline() -> None:
    result = compute_drift_signals(12.0, 10000.0, [])
    assert result["has_baseline"] is False
    assert result["detection_method"] == "none"
    assert result["mape_drift"] is False


def test_summarize_drift_metrics_counts_methods() -> None:
    metrics = [
        {"drift": {"mape_drift": True, "cost_drift": False, "detection_method": "z_score", "drift_severity": "warn"}},
        {"drift": {"mape_drift": False, "cost_drift": True, "detection_method": "legacy_threshold", "drift_severity": "crit"}},
    ]
    summary = summarize_drift_metrics(metrics)

    assert summary["sample_size"] == 2
    assert summary["mape_drift_runs"] == 1
    assert summary["cost_drift_runs"] == 1
    assert summary["z_score_detections"] == 1
    assert summary["legacy_detections"] == 1


def test_monitoring_drift_summary_endpoint(auth_headers: dict[str, str]) -> None:
    client = TestClient(app)
    trigger = client.post(
        "/api/v1/pipeline/trigger-pipeline",
        json={"asset_id": "RES-BAL-01", "target_date": "2026-07-06"},
        headers=auth_headers,
    )
    assert trigger.status_code == 200, trigger.text

    response = client.get("/api/v1/monitoring/drift-summary?limit=20", headers=auth_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["version"] == DRIFT_DETECTION_VERSION
    assert "severity_counts" in data
    assert "mape_drift_runs" in data
