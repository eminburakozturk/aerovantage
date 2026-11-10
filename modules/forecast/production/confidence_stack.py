"""Prediction -> Confidence -> Prediction Interval -> Coverage stack."""

from __future__ import annotations

from typing import Any

CONFIDENCE_STACK_VERSION = "1.0.0"
_DEFAULT_COVERAGE_TARGET = 0.80


def compute_base_confidence(risk_score: int, mape_percentage: float) -> int:
    adjustment = 5 if mape_percentage < 12 else -5 if mape_percentage > 18 else 0
    return max(0, min(100, 100 - int(risk_score) + adjustment))


def compute_calibrated_confidence(base_confidence: int, drift: dict[str, Any]) -> int:
    penalty = min(25.0, max(0.0, float(drift.get("mape_delta", 0.0)) * 2.0))
    if drift.get("detection_method") == "z_score":
        penalty = max(penalty, min(25.0, abs(float(drift.get("mape_z_score", 0.0))) * 5.0))
    return max(0, min(100, int(base_confidence - penalty)))


def prediction_interval(
    forecast_mw: float,
    mape_percentage: float,
    *,
    confidence: int,
) -> dict[str, float]:
    confidence_factor = 1.0 + max(0.0, (70.0 - float(confidence)) / 100.0)
    margin_pct = max(mape_percentage, 5.0) * confidence_factor / 100.0
    margin_mw = forecast_mw * margin_pct
    return {
        "point_mw": round(forecast_mw, 4),
        "lower_mw": round(max(0.0, forecast_mw - margin_mw), 4),
        "upper_mw": round(forecast_mw + margin_mw, 4),
        "margin_mw": round(margin_mw, 4),
        "margin_pct": round(margin_pct * 100.0, 4),
    }


def compute_coverage(
    hours: list[dict[str, Any]],
    intervals: list[dict[str, Any]],
    *,
    target: float = _DEFAULT_COVERAGE_TARGET,
) -> dict[str, Any]:
    covered = 0
    evaluated = 0
    for hour, interval in zip(hours, intervals):
        actual = hour.get("actual_mw")
        if actual is None:
            continue
        evaluated += 1
        actual_mw = float(actual)
        if float(interval["lower_mw"]) <= actual_mw <= float(interval["upper_mw"]):
            covered += 1

    coverage_rate = round(covered / evaluated, 4) if evaluated else 0.0
    return {
        "covered_hours": covered,
        "evaluated_hours": evaluated,
        "coverage_rate": coverage_rate,
        "target_coverage": target,
        "meets_target": coverage_rate >= target if evaluated else False,
    }


def build_confidence_stack(
    *,
    risk_score: int,
    mape_percentage: float,
    drift: dict[str, Any],
    hours: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build full confidence stack for a pipeline run."""
    base_confidence = compute_base_confidence(risk_score, mape_percentage)
    confidence_calibrated = compute_calibrated_confidence(base_confidence, drift)

    normalized_hours = [
        {
            "timestamp": hour.get("timestamp"),
            "forecast_mw": float(hour.get("forecast_mw") or hour.get("generated_mw") or 0.0),
            "actual_mw": hour.get("actual_mw"),
        }
        for hour in hours
    ]
    hourly_intervals = [
        {
            "timestamp": hour["timestamp"],
            **prediction_interval(
                hour["forecast_mw"],
                mape_percentage,
                confidence=confidence_calibrated,
            ),
        }
        for hour in normalized_hours
    ]
    coverage = compute_coverage(normalized_hours, hourly_intervals)

    if normalized_hours:
        avg_forecast = sum(hour["forecast_mw"] for hour in normalized_hours) / len(normalized_hours)
    else:
        avg_forecast = 0.0

    return {
        "version": CONFIDENCE_STACK_VERSION,
        "base_confidence": base_confidence,
        "confidence_calibrated": confidence_calibrated,
        "prediction_interval": prediction_interval(
            avg_forecast,
            mape_percentage,
            confidence=confidence_calibrated,
        ),
        "hourly_intervals": hourly_intervals,
        "coverage": coverage,
    }
