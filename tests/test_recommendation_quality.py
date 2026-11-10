"""Recommendation quality proxy metric tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from modules.recommendation.quality import (
    RECOMMENDATION_QUALITY_VERSION,
    build_weekly_report,
    evaluate_recommendation_quality,
)


def _run(
    *,
    risk: float,
    cost: float,
    mape: float,
    action: str = "Pozisyonu azalt",
) -> dict:
    return {
        "asset_id": "RES-BAL-01",
        "risk_score": risk,
        "total_imbalance_cost_tl": cost,
        "mape_percentage": mape,
        "action_plan": action,
    }


def test_evaluate_recommendation_quality_empty_samples() -> None:
    result = evaluate_recommendation_quality([])
    assert result["samples"] == 0
    assert result["reportable"] is False
    assert result["quality_score"] == 0.0
    assert result["version"] == RECOMMENDATION_QUALITY_VERSION


def test_evaluate_recommendation_quality_detects_improvement() -> None:
    runs = [
        _run(risk=80, cost=60000, mape=18),
        _run(risk=55, cost=42000, mape=14),
        _run(risk=40, cost=30000, mape=11),
    ]
    result = evaluate_recommendation_quality(runs, period_days=7)

    assert result["samples"] == 3
    assert result["evaluated_actions"] == 2
    assert result["action_coverage"] == 1.0
    assert result["improved_after_action_ratio"] == 1.0
    assert result["cost_improved_after_action_ratio"] == 1.0
    assert result["mape_improved_after_action_ratio"] == 1.0
    assert result["quality_score"] > 80
    assert result["reportable"] is True


def test_evaluate_ignores_default_monitoring_action() -> None:
    runs = [
        _run(risk=70, cost=50000, mape=16, action="Standart izleme prosedürüne devam et"),
        _run(risk=65, cost=48000, mape=15),
    ]
    result = evaluate_recommendation_quality(runs)
    assert result["evaluated_actions"] == 0
    assert result["reportable"] is False


def test_build_weekly_report_includes_asset_id() -> None:
    report = build_weekly_report("RES-BAL-01", storage=None, days=7)
    assert report["asset_id"] == "RES-BAL-01"
    assert report["period_days"] == 7
    assert "quality_score" in report


def test_monitoring_recommendation_quality_endpoint(auth_headers: dict[str, str]) -> None:
    client = TestClient(app)
    trigger = client.post(
        "/api/v1/pipeline/trigger-pipeline",
        json={"asset_id": "RES-BAL-01", "target_date": "2026-07-06"},
        headers=auth_headers,
    )
    assert trigger.status_code == 200, trigger.text

    response = client.get(
        "/api/v1/monitoring/recommendation-quality?asset_id=RES-BAL-01&days=7",
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["asset_id"] == "RES-BAL-01"
    assert data["version"] == RECOMMENDATION_QUALITY_VERSION
    assert "quality_score" in data
    assert "reportable" in data
    assert "improved_after_action_ratio" in data
