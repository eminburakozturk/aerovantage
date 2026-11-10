"""FAZ 3 — model reliability gate testleri."""

from __future__ import annotations

import pytest

from modules.forecast.production.confidence_stack import build_confidence_stack
from modules.forecast.production.model_reliability import (
    ModelReliabilityGateError,
    enforce_model_reliability_gate,
    merge_model_reliability_reports,
    run_model_reliability_gate,
)
from modules.forecast.production.validation import walk_forward_time_series_validation
from modules.monitoring.drift import compute_drift_signals


def test_walk_forward_validation_produces_folds() -> None:
    features = [[float(i)] for i in range(20)]
    targets = [float(i) for i in range(20)]
    result = walk_forward_time_series_validation(features, targets)
    assert result["fold_count"] >= 1
    assert result["mean_val_mae"] is not None


def test_model_reliability_gate_passes_for_physics_only() -> None:
    report = run_model_reliability_gate(model_info={"type": "physics_only"})
    assert report.gate_passed


def test_model_reliability_gate_rejects_undeployable_hybrid() -> None:
    report = run_model_reliability_gate(
        model_info={
            "type": "hybrid_xgb",
            "validation": {
                "deployable": False,
                "acceptance_gate": {"passed": False},
                "promotion": {"promoted": False},
                "walk_forward": {"passed": False},
            },
        }
    )
    assert not report.gate_passed


def test_model_reliability_gate_accepts_deployable_hybrid() -> None:
    report = run_model_reliability_gate(
        model_info={
            "type": "hybrid_xgb",
            "validation": {
                "deployable": True,
                "version": "1.0.0",
                "acceptance_gate": {"passed": True},
                "promotion": {"promoted": True},
                "walk_forward": {"passed": True, "fold_count": 3},
            },
        }
    )
    assert report.gate_passed


def test_model_reliability_full_stack_contracts() -> None:
    drift = compute_drift_signals(12.0, 10000.0, [])
    confidence_stack = build_confidence_stack(
        risk_score=30,
        mape_percentage=10.0,
        drift=drift,
        hours=[{"timestamp": "2026-07-07T08:00:00", "forecast_mw": 10.0, "actual_mw": 10.2}],
    )
    report = run_model_reliability_gate(
        model_info={"type": "physics_only"},
        drift=drift,
        confidence_stack=confidence_stack,
    )
    assert report.gate_passed


def test_enforce_model_reliability_gate_raises() -> None:
    report = run_model_reliability_gate(
        model_info={"type": "hybrid_xgb", "validation": {"deployable": False}},
    )
    with pytest.raises(ModelReliabilityGateError):
        enforce_model_reliability_gate(report)


def test_merge_model_reliability_reports() -> None:
    first = run_model_reliability_gate(model_info={"type": "physics_only"})
    second = run_model_reliability_gate(model_info={"type": "physics_only"})
    merged = merge_model_reliability_reports(first, second)
    assert merged.gate_passed
    assert len(merged.checks) == len(first.checks) + len(second.checks)
