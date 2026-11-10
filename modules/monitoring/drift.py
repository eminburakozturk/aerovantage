"""Statistical drift and residual monitoring for model/operational metrics."""

from __future__ import annotations

import math
from typing import Any, Sequence

DRIFT_DETECTION_VERSION = "2.0.0"
DEFAULT_BASELINE_WINDOW = 7
MIN_SAMPLES_FOR_ZSCORE = 3
Z_SCORE_DRIFT_THRESHOLD = 2.0
LEGACY_MAPE_DELTA_THRESHOLD = 3.0
LEGACY_COST_DELTA_THRESHOLD = 20000.0
_STD_EPSILON = 1e-6


def _baseline_stats(values: Sequence[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    mean = sum(values) / len(values)
    if len(values) < 2:
        return mean, 0.0
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return mean, math.sqrt(variance)


def _severity_from_signal(z_score: float, delta: float, *, legacy_threshold: float) -> str:
    if z_score >= 3.0 or delta >= legacy_threshold * 1.5:
        return "crit"
    if z_score >= Z_SCORE_DRIFT_THRESHOLD or delta >= legacy_threshold:
        return "warn"
    return "normal"


def compute_drift_signals(
    current_mape: float,
    current_cost: float,
    recent_metrics: list[dict[str, Any]],
    *,
    baseline_window: int = DEFAULT_BASELINE_WINDOW,
) -> dict[str, Any]:
    """Detect drift using z-score when enough baseline samples exist, else legacy thresholds."""
    if not recent_metrics:
        return {
            "version": DRIFT_DETECTION_VERSION,
            "has_baseline": False,
            "detection_method": "none",
            "mape_drift": False,
            "cost_drift": False,
            "mape_delta": 0.0,
            "cost_delta": 0.0,
            "residual_mape": 0.0,
            "residual_cost": 0.0,
            "mape_z_score": 0.0,
            "cost_z_score": 0.0,
            "drift_severity": "normal",
            "baseline_samples": 0,
        }

    baseline_window_items = recent_metrics[:baseline_window]
    mape_series = [float(item.get("mape_percentage", 0.0)) for item in baseline_window_items]
    cost_series = [float(item.get("total_imbalance_cost_tl", 0.0)) for item in baseline_window_items]
    baseline_mape, mape_std = _baseline_stats(mape_series)
    baseline_cost, cost_std = _baseline_stats(cost_series)

    residual_mape = current_mape - baseline_mape
    residual_cost = current_cost - baseline_cost

    if len(mape_series) >= MIN_SAMPLES_FOR_ZSCORE:
        detection_method = "z_score"
        mape_z = residual_mape / mape_std if mape_std > _STD_EPSILON else 0.0
        cost_z = residual_cost / cost_std if cost_std > _STD_EPSILON else 0.0
        mape_drift = mape_z >= Z_SCORE_DRIFT_THRESHOLD
        cost_drift = cost_z >= Z_SCORE_DRIFT_THRESHOLD
    else:
        detection_method = "legacy_threshold"
        mape_z = 0.0
        cost_z = 0.0
        mape_drift = residual_mape >= LEGACY_MAPE_DELTA_THRESHOLD
        cost_drift = residual_cost >= LEGACY_COST_DELTA_THRESHOLD

    mape_severity = _severity_from_signal(
        mape_z if detection_method == "z_score" else 0.0,
        residual_mape,
        legacy_threshold=LEGACY_MAPE_DELTA_THRESHOLD,
    )
    cost_severity = _severity_from_signal(
        cost_z if detection_method == "z_score" else 0.0,
        residual_cost,
        legacy_threshold=LEGACY_COST_DELTA_THRESHOLD,
    )
    severity_rank = {"normal": 0, "warn": 1, "crit": 2}
    drift_severity = max(mape_severity, cost_severity, key=lambda item: severity_rank[item])

    return {
        "version": DRIFT_DETECTION_VERSION,
        "has_baseline": True,
        "detection_method": detection_method,
        "mape_drift": mape_drift,
        "cost_drift": cost_drift,
        "mape_delta": round(residual_mape, 4),
        "cost_delta": round(residual_cost, 2),
        "residual_mape": round(residual_mape, 4),
        "residual_cost": round(residual_cost, 2),
        "mape_z_score": round(mape_z, 4),
        "cost_z_score": round(cost_z, 4),
        "baseline_mape": round(baseline_mape, 4),
        "baseline_cost": round(baseline_cost, 2),
        "baseline_mape_std": round(mape_std, 4),
        "baseline_cost_std": round(cost_std, 2),
        "baseline_samples": len(baseline_window_items),
        "drift_severity": drift_severity,
        "z_score_threshold": Z_SCORE_DRIFT_THRESHOLD,
    }


def summarize_drift_metrics(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate drift signals across stored metric records."""
    total = len(metrics)
    mape_drift_count = 0
    cost_drift_count = 0
    z_score_count = 0
    legacy_count = 0
    severity_counts = {"normal": 0, "warn": 0, "crit": 0}

    for item in metrics:
        drift = item.get("drift") or {}
        if drift.get("mape_drift"):
            mape_drift_count += 1
        if drift.get("cost_drift"):
            cost_drift_count += 1
        method = drift.get("detection_method")
        if method == "z_score":
            z_score_count += 1
        elif method == "legacy_threshold":
            legacy_count += 1
        severity = str(drift.get("drift_severity") or "normal")
        if severity in severity_counts:
            severity_counts[severity] += 1

    return {
        "version": DRIFT_DETECTION_VERSION,
        "sample_size": total,
        "mape_drift_runs": mape_drift_count,
        "cost_drift_runs": cost_drift_count,
        "z_score_detections": z_score_count,
        "legacy_detections": legacy_count,
        "severity_counts": severity_counts,
    }
