"""Model validation framework tests."""

from __future__ import annotations

import pytest

from modules.forecast.production.validation import (
    VALIDATION_FRAMEWORK_VERSION,
    AcceptanceCriteria,
    build_validation_report,
    evaluate_acceptance_gate,
    evaluate_promotion,
    regression_metrics,
    split_time_series_chronological,
)


def test_split_time_series_uses_latest_rows_for_validation() -> None:
    features = [[float(i)] for i in range(10)]
    targets = [float(i) for i in range(10)]
    split = split_time_series_chronological(features, targets, val_ratio=0.2, min_val_samples=2)

    assert split.train_size == 8
    assert split.val_size == 2
    assert split.y_val.tolist() == [8.0, 9.0]


def test_regression_metrics_basic() -> None:
    metrics = regression_metrics([10.0, 20.0], [11.0, 18.0])
    assert metrics["mae"] == 1.5
    assert metrics["rmse"] == pytest.approx(1.5811, rel=1e-3)


def test_acceptance_gate_rejects_high_validation_error() -> None:
    result = evaluate_acceptance_gate(
        {"mae": 1.0},
        {"mae": 12.0},
        criteria=AcceptanceCriteria(max_val_mae=8.0),
        val_samples=6,
    )
    assert result["passed"] is False
    assert "val_mae>8.0" in result["reasons"]


def test_acceptance_gate_rejects_overfit_gap() -> None:
    result = evaluate_acceptance_gate(
        {"mae": 1.0},
        {"mae": 6.0},
        criteria=AcceptanceCriteria(max_val_mae=8.0, max_train_val_mae_gap=3.0),
        val_samples=6,
    )
    assert result["passed"] is False
    assert "train_val_gap>3.0" in result["reasons"]


def test_promotion_requires_improvement_over_incumbent() -> None:
    improved = evaluate_promotion(4.5, 5.0)
    rejected = evaluate_promotion(5.2, 5.0)

    assert improved["promoted"] is True
    assert rejected["promoted"] is False
    assert rejected["reason"] == "incumbent_better"


def test_build_validation_report_marks_deployable_candidate() -> None:
    report = build_validation_report(
        train_metrics={"mae": 2.0, "rmse": 2.5, "mape_pct": 5.0},
        val_metrics={"mae": 3.0, "rmse": 3.5, "mape_pct": 6.0},
        val_samples=6,
        incumbent_val_mae=4.0,
    )
    assert report["version"] == VALIDATION_FRAMEWORK_VERSION
    assert report["deployable"] is True
    assert report["acceptance_gate"]["passed"] is True
    assert report["promotion"]["promoted"] is True


def test_build_validation_report_blocks_non_deployable_candidate() -> None:
    report = build_validation_report(
        train_metrics={"mae": 1.0, "rmse": 1.2, "mape_pct": 2.0},
        val_metrics={"mae": 10.0, "rmse": 11.0, "mape_pct": 20.0},
        val_samples=6,
        incumbent_val_mae=None,
    )
    assert report["deployable"] is False


def test_build_validation_report_requires_walk_forward_pass() -> None:
    report = build_validation_report(
        train_metrics={"mae": 2.0, "rmse": 2.5, "mape_pct": 5.0},
        val_metrics={"mae": 3.0, "rmse": 3.5, "mape_pct": 6.0},
        val_samples=6,
        incumbent_val_mae=4.0,
        walk_forward={"passed": False, "mean_val_mae": 12.0},
    )
    assert report["deployable"] is False
