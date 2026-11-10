"""Confidence stack tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from modules.forecast.production.confidence_stack import (
    CONFIDENCE_STACK_VERSION,
    build_confidence_stack,
    compute_base_confidence,
    compute_calibrated_confidence,
    compute_coverage,
    prediction_interval,
)


def test_compute_base_confidence_adjusts_for_mape() -> None:
    low_mape = compute_base_confidence(40, 10.0)
    high_mape = compute_base_confidence(40, 20.0)
    assert low_mape > high_mape


def test_compute_calibrated_confidence_penalizes_drift() -> None:
    base = 80
    drift = {"mape_delta": 4.0, "detection_method": "legacy_threshold"}
    calibrated = compute_calibrated_confidence(base, drift)
    assert calibrated < base


def test_prediction_interval_widens_with_lower_confidence() -> None:
    tight = prediction_interval(20.0, 10.0, confidence=80)
    wide = prediction_interval(20.0, 10.0, confidence=40)
    assert wide["margin_mw"] > tight["margin_mw"]


def test_compute_coverage_counts_hours_in_band() -> None:
    hours = [
        {"forecast_mw": 10.0, "actual_mw": 10.5},
        {"forecast_mw": 12.0, "actual_mw": 20.0},
    ]
    intervals = [
        {"lower_mw": 9.0, "upper_mw": 11.0},
        {"lower_mw": 11.0, "upper_mw": 13.0},
    ]
    coverage = compute_coverage(hours, intervals)
    assert coverage["evaluated_hours"] == 2
    assert coverage["covered_hours"] == 1
    assert coverage["coverage_rate"] == 0.5


def test_build_confidence_stack_full_chain() -> None:
    hours = [
        {"timestamp": "2026-07-07T08:00:00", "forecast_mw": 10.0, "actual_mw": 10.2},
        {"timestamp": "2026-07-07T09:00:00", "forecast_mw": 12.0, "actual_mw": 11.5},
    ]
    stack = build_confidence_stack(
        risk_score=35,
        mape_percentage=12.0,
        drift={"mape_delta": 1.0, "detection_method": "legacy_threshold"},
        hours=hours,
    )

    assert stack["version"] == CONFIDENCE_STACK_VERSION
    assert 0 <= stack["base_confidence"] <= 100
    assert 0 <= stack["confidence_calibrated"] <= 100
    assert "lower_mw" in stack["prediction_interval"]
    assert len(stack["hourly_intervals"]) == 2
    assert "coverage_rate" in stack["coverage"]


def test_monitoring_confidence_stack_endpoint(auth_headers: dict[str, str]) -> None:
    client = TestClient(app)
    trigger = client.post(
        "/api/v1/pipeline/trigger-pipeline",
        json={"asset_id": "RES-BAL-01", "target_date": "2026-07-06"},
        headers=auth_headers,
    )
    assert trigger.status_code == 200, trigger.text
    metadata = trigger.json()["metadata"]
    assert "confidence_stack" in metadata

    response = client.get(
        "/api/v1/monitoring/confidence-stack?asset_id=RES-BAL-01",
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["found"] is True
    assert data["version"] == CONFIDENCE_STACK_VERSION
    assert "coverage" in data
