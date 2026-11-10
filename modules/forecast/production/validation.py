"""Time-series validation, acceptance gate, and retrain promotion criteria."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

VALIDATION_FRAMEWORK_VERSION = "1.0.0"


@dataclass(frozen=True)
class AcceptanceCriteria:
    max_val_mae: float = 8.0
    max_train_val_mae_gap: float = 3.0
    min_val_samples: int = 4


@dataclass(frozen=True)
class TimeSeriesSplitResult:
    x_train: np.ndarray
    y_train: np.ndarray
    x_val: np.ndarray
    y_val: np.ndarray
    train_size: int
    val_size: int


DEFAULT_ACCEPTANCE_CRITERIA = AcceptanceCriteria()


def split_time_series_chronological(
    features: Sequence[Sequence[float]],
    targets: Sequence[float],
    *,
    val_ratio: float = 0.2,
    min_val_samples: int = 4,
) -> TimeSeriesSplitResult:
    """Chronological hold-out: earliest rows train, latest rows validation."""
    x = np.asarray(features, dtype=float)
    y = np.asarray(targets, dtype=float)
    if len(x) != len(y):
        raise ValueError("features and targets length mismatch")
    if len(x) < min_val_samples + 1:
        split_index = max(1, len(x) - 1)
    else:
        val_size = max(min_val_samples, int(len(x) * val_ratio))
        val_size = min(val_size, len(x) - 1)
        split_index = len(x) - val_size

    return TimeSeriesSplitResult(
        x_train=x[:split_index],
        y_train=y[:split_index],
        x_val=x[split_index:],
        y_val=y[split_index:],
        train_size=split_index,
        val_size=len(x) - split_index,
    )


def regression_metrics(y_true: Sequence[float], y_pred: Sequence[float]) -> dict[str, float]:
    true = np.asarray(y_true, dtype=float)
    pred = np.asarray(y_pred, dtype=float)
    if len(true) == 0:
        return {"mae": 0.0, "rmse": 0.0, "mape_pct": 0.0}
    errors = pred - true
    mae = float(np.abs(errors).mean())
    rmse = float(np.sqrt((errors**2).mean()))
    denom = np.maximum(np.abs(true), 1e-6)
    mape_pct = float((np.abs(errors) / denom).mean() * 100.0)
    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "mape_pct": round(mape_pct, 4),
    }


def evaluate_acceptance_gate(
    train_metrics: dict[str, float],
    val_metrics: dict[str, float],
    *,
    criteria: AcceptanceCriteria = DEFAULT_ACCEPTANCE_CRITERIA,
    val_samples: int,
) -> dict[str, Any]:
    """Return whether candidate model passes production acceptance thresholds."""
    reasons: list[str] = []
    val_mae = float(val_metrics.get("mae", 0.0))
    train_mae = float(train_metrics.get("mae", 0.0))
    gap = val_mae - train_mae

    if val_samples < criteria.min_val_samples:
        reasons.append(f"val_samples<{criteria.min_val_samples}")
    if val_mae > criteria.max_val_mae:
        reasons.append(f"val_mae>{criteria.max_val_mae}")
    if gap > criteria.max_train_val_mae_gap:
        reasons.append(f"train_val_gap>{criteria.max_train_val_mae_gap}")

    passed = len(reasons) == 0
    return {
        "passed": passed,
        "reasons": reasons,
        "criteria": {
            "max_val_mae": criteria.max_val_mae,
            "max_train_val_mae_gap": criteria.max_train_val_mae_gap,
            "min_val_samples": criteria.min_val_samples,
        },
        "train_metrics": train_metrics,
        "val_metrics": val_metrics,
        "train_val_mae_gap": round(val_mae - train_mae, 4),
    }


def evaluate_promotion(
    candidate_val_mae: float,
    incumbent_val_mae: float | None,
    *,
    improvement_margin: float = 0.0,
) -> dict[str, Any]:
    """Decide whether a retrained candidate should replace the incumbent artifact."""
    if incumbent_val_mae is None:
        return {
            "promoted": True,
            "reason": "no_incumbent",
            "incumbent_val_mae": None,
            "candidate_val_mae": round(candidate_val_mae, 4),
        }

    promoted = candidate_val_mae <= (incumbent_val_mae - improvement_margin)
    reason = "improved_or_equal" if promoted else "incumbent_better"
    return {
        "promoted": promoted,
        "reason": reason,
        "incumbent_val_mae": round(incumbent_val_mae, 4),
        "candidate_val_mae": round(candidate_val_mae, 4),
    }


def build_validation_report(
    *,
    train_metrics: dict[str, float],
    val_metrics: dict[str, float],
    val_samples: int,
    incumbent_val_mae: float | None,
    criteria: AcceptanceCriteria = DEFAULT_ACCEPTANCE_CRITERIA,
    walk_forward: dict[str, Any] | None = None,
) -> dict[str, Any]:
    acceptance = evaluate_acceptance_gate(
        train_metrics,
        val_metrics,
        criteria=criteria,
        val_samples=val_samples,
    )
    promotion = evaluate_promotion(val_metrics["mae"], incumbent_val_mae)
    walk_forward_passed = True if walk_forward is None else bool(walk_forward.get("passed"))
    deployable = acceptance["passed"] and promotion["promoted"] and walk_forward_passed
    return {
        "version": VALIDATION_FRAMEWORK_VERSION,
        "split": "chronological_holdout",
        "acceptance_gate": acceptance,
        "promotion": promotion,
        "walk_forward": walk_forward,
        "deployable": deployable,
    }


def walk_forward_time_series_validation(
    features: Sequence[Sequence[float]],
    targets: Sequence[float],
    *,
    n_folds: int = 3,
    min_train_size: int = 8,
    val_ratio: float = 0.15,
    max_mean_val_mae: float = DEFAULT_ACCEPTANCE_CRITERIA.max_val_mae,
) -> dict[str, Any]:
    """Expanding-window walk-forward validation over chronological folds."""
    x = np.asarray(features, dtype=float)
    y = np.asarray(targets, dtype=float)
    if len(x) != len(y):
        raise ValueError("features and targets length mismatch")
    if len(x) < min_train_size + 2:
        return {
            "passed": False,
            "reason": "insufficient_samples",
            "fold_count": 0,
            "mean_val_mae": None,
            "folds": [],
        }

    val_size = max(2, int(len(x) * val_ratio))
    folds: list[dict[str, Any]] = []
    max_start = len(x) - val_size
    step = max(1, (max_start - min_train_size) // max(1, n_folds - 1)) if n_folds > 1 else max_start

    for fold_index in range(n_folds):
        train_end = min(max_start, min_train_size + fold_index * step)
        if train_end < min_train_size:
            continue
        val_end = min(len(x), train_end + val_size)
        if val_end <= train_end:
            continue

        y_val = y[train_end:val_end]
        y_train = y[:train_end]
        train_mean = float(np.mean(y_train))
        val_pred = np.full(len(y_val), train_mean)
        val_metrics = regression_metrics(y_val, val_pred)
        folds.append(
            {
                "fold_index": fold_index,
                "train_size": train_end,
                "val_size": val_end - train_end,
                "val_metrics": val_metrics,
            }
        )

    if not folds:
        return {
            "passed": False,
            "reason": "no_folds",
            "fold_count": 0,
            "mean_val_mae": None,
            "folds": [],
        }

    mean_val_mae = float(np.mean([fold["val_metrics"]["mae"] for fold in folds]))
    passed = mean_val_mae <= max_mean_val_mae
    return {
        "passed": passed,
        "reason": "ok" if passed else "mean_val_mae_exceeded",
        "fold_count": len(folds),
        "mean_val_mae": round(mean_val_mae, 4),
        "max_mean_val_mae": max_mean_val_mae,
        "folds": folds,
    }
