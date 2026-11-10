"""Decision causality loop tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from modules.recommendation.causality import (
    CAUSALITY_VERSION,
    build_causality_report,
    evaluate_decision_causality,
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


def test_evaluate_decision_causality_positive_lift() -> None:
    runs = [
        _run(risk=70, cost=60000, mape=18),
        _run(risk=50, cost=42000, mape=14),
        _run(risk=48, cost=40000, mape=13),
        _run(risk=47, cost=39000, mape=12, action="Standart izleme prosedürüne devam et"),
        _run(risk=46, cost=38000, mape=12, action="Standart izleme prosedürüne devam et"),
    ]
    result = evaluate_decision_causality(runs)

    assert result["version"] == CAUSALITY_VERSION
    assert result["action_pairs"] >= 1
    assert result["control_pairs"] >= 1
    assert result["causality_lift"] > 0
    assert result["causality_signal"] == "positive"
    assert result["reportable"] is True


def test_evaluate_decision_causality_not_reportable_with_single_pair_type() -> None:
    runs = [
        _run(risk=70, cost=60000, mape=18),
        _run(risk=50, cost=42000, mape=14),
    ]
    result = evaluate_decision_causality(runs)
    assert result["reportable"] is False


def test_build_causality_report_includes_asset_id() -> None:
    report = build_causality_report("RES-BAL-01", storage=None, days=7)
    assert report["asset_id"] == "RES-BAL-01"
    assert "causality_lift" in report


def test_monitoring_decision_causality_endpoint(auth_headers: dict[str, str]) -> None:
    client = TestClient(app)
    trigger = client.post(
        "/api/v1/pipeline/trigger-pipeline",
        json={"asset_id": "RES-BAL-01", "target_date": "2026-07-06"},
        headers=auth_headers,
    )
    assert trigger.status_code == 200, trigger.text
    assert "decision_causality" in trigger.json()["metadata"]

    response = client.get(
        "/api/v1/monitoring/decision-causality?asset_id=RES-BAL-01&days=7",
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["asset_id"] == "RES-BAL-01"
    assert data["version"] == CAUSALITY_VERSION
    assert "causality_lift" in data
