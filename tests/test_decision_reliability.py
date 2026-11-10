"""FAZ 4 — decision reliability gate testleri."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from modules.ai.schemas import AIResponse
from modules.alerting.quality import evaluate_alert_quality
from modules.recommendation.decision_reliability import (
    DecisionReliabilityGateError,
    enforce_decision_reliability_gate,
    is_action_risk_aligned,
    run_decision_reliability_gate,
)
from modules.recommendation.quality import evaluate_recommendation_quality
from modules.risk.schemas import DailyRiskScoreResponse, HourlyRiskData


def _risk_response() -> DailyRiskScoreResponse:
    hours = [
        HourlyRiskData(
            timestamp=datetime(2026, 7, 6, hour, tzinfo=timezone.utc),
            forecast_mw=10.0,
            actual_mw=9.0,
            ptf_price=2800.0,
            imbalance_cost_tl=round(abs(1.0) * 2800.0 * 0.03, 2),
        )
        for hour in range(24)
    ]
    total = round(sum(hour.imbalance_cost_tl for hour in hours), 2)
    score = min(int((total / 10000.0) * 100), 100)
    return DailyRiskScoreResponse(
        target_date=date(2026, 7, 6),
        total_imbalance_cost_tl=total,
        risk_score=score,
        hours=hours,
        market_source="epias-live",
    )


def test_is_action_risk_aligned_rejects_monitoring_on_high_risk() -> None:
    assert is_action_risk_aligned(
        {"risk_score": 70, "total_imbalance_cost_tl": 5000},
        "Standart izleme prosedürüne devam et",
    ) is False
    assert is_action_risk_aligned(
        {"risk_score": 70, "total_imbalance_cost_tl": 5000},
        "Pozisyonu azalt",
    ) is True


def test_decision_gate_passes_for_playbook_aligned_mock_flow() -> None:
    risk_data = {
        "risk_score": 70,
        "total_imbalance_cost_tl": 5000,
        "forecast_mw": 20,
        "wind_speed_mps": 8,
        "mape_percentage": 12,
    }
    report = run_decision_reliability_gate(
        risk_data=risk_data,
        risk_response=_risk_response(),
        ai_response=AIResponse(insight="test", action_plan="Pozisyonu azalt"),
        model_attribution={
            "version": "1.0.0",
            "method": "physics_only",
            "features": [{"feature": "physics_mw", "shap_value": 1.0, "weight": 1.0}],
        },
        model_info={"type": "physics_only"},
        strict_playbook=True,
    )
    assert report.gate_passed


def test_decision_gate_rejects_missing_ai_output() -> None:
    report = run_decision_reliability_gate(
        risk_data={"risk_score": 10, "total_imbalance_cost_tl": 100},
        risk_response=_risk_response(),
        ai_response=AIResponse(insight="", action_plan=""),
        model_attribution=None,
        model_info={"type": "physics_only"},
    )
    assert not report.gate_passed


def test_alert_quality_includes_false_negative_metrics() -> None:
    runs = [
        {
            "risk_score": 70,
            "mape_percentage": 18,
            "total_imbalance_cost_tl": 60000,
            "alert_status": {"severity": "INFO"},
            "rules": [],
        },
        {
            "risk_score": 72,
            "mape_percentage": 17,
            "total_imbalance_cost_tl": 62000,
            "alert_status": {"severity": "WARNING"},
            "rules": [],
        },
    ]
    result = evaluate_alert_quality(runs)
    assert "false_negative_rate" in result
    assert result["false_negative_proxy"] >= 1


def test_decision_gate_with_weekly_metric_contracts() -> None:
    runs = [
        {
            "asset_id": "RES-BAL-01",
            "risk_score": 80,
            "total_imbalance_cost_tl": 60000,
            "mape_percentage": 18,
            "action_plan": "Pozisyonu azalt",
        },
        {
            "asset_id": "RES-BAL-01",
            "risk_score": 55,
            "total_imbalance_cost_tl": 42000,
            "mape_percentage": 14,
            "action_plan": "Pozisyonu azalt",
        },
    ]
    report = run_decision_reliability_gate(
        risk_data={"risk_score": 55, "total_imbalance_cost_tl": 42000, "forecast_mw": 20, "wind_speed_mps": 8},
        risk_response=_risk_response(),
        ai_response=AIResponse(insight="ok", action_plan="Pozisyonu azalt"),
        model_attribution={"version": "1.0.0", "method": "physics_only", "features": [{"feature": "physics_mw", "weight": 1.0}]},
        model_info={"type": "physics_only"},
        recommendation_quality=evaluate_recommendation_quality(runs),
        alert_quality=evaluate_alert_quality(runs),
        decision_causality={"version": "1.0.0", "causality_lift": 1.0, "causality_signal": "positive", "action_pairs": 1, "control_pairs": 0, "reportable": False},
        strict_playbook=True,
    )
    assert report.gate_passed


def test_enforce_decision_gate_raises() -> None:
    from modules.recommendation.decision_reliability import DecisionReliabilityReport

    with pytest.raises(DecisionReliabilityGateError):
        enforce_decision_reliability_gate(DecisionReliabilityReport(gate_passed=False))
