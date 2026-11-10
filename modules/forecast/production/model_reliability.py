"""FAZ 3 — model reliability gate ve doğrulama orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from modules.forecast.production.confidence_stack import CONFIDENCE_STACK_VERSION
from modules.forecast.production.feature_schema import (
    FEATURE_SCHEMA_VERSION,
    HYBRID_FEATURE_NAMES,
    assert_no_leakage_features,
    build_inference_vector,
    build_training_vector,
    validate_feature_names,
    validate_feature_vector,
)
from modules.forecast.production.validation import VALIDATION_FRAMEWORK_VERSION
from modules.monitoring.drift import DRIFT_DETECTION_VERSION

MODEL_RELIABILITY_VERSION = "1.0.0"


@dataclass(frozen=True)
class ModelReliabilityCheck:
    name: str
    category: str
    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelReliabilityReport:
    gate_passed: bool
    checks: list[ModelReliabilityCheck] = field(default_factory=list)
    model_type: str = "unknown"
    validation_framework_version: str = VALIDATION_FRAMEWORK_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": MODEL_RELIABILITY_VERSION,
            "gate_passed": self.gate_passed,
            "model_type": self.model_type,
            "validation_framework_version": self.validation_framework_version,
            "checks": [
                {
                    "name": check.name,
                    "category": check.category,
                    "passed": check.passed,
                    "message": check.message,
                    "details": check.details,
                }
                for check in self.checks
            ],
        }


def merge_model_reliability_reports(*reports: ModelReliabilityReport) -> ModelReliabilityReport:
    checks: list[ModelReliabilityCheck] = []
    for report in reports:
        checks.extend(report.checks)
    model_type = reports[-1].model_type if reports else "unknown"
    gate_passed = all(report.gate_passed for report in reports)
    return ModelReliabilityReport(
        gate_passed=gate_passed,
        checks=checks,
        model_type=model_type,
    )


class ModelReliabilityGateError(RuntimeError):
    """Model reliability gate başarısız olduğu için pipeline durduruldu."""

    def __init__(self, report: ModelReliabilityReport) -> None:
        self.report = report
        super().__init__(f"Model reliability gate failed (model_type={report.model_type})")


def run_model_reliability_gate(
    *,
    model_info: dict[str, Any],
    confidence_stack: dict[str, Any] | None = None,
    drift: dict[str, Any] | None = None,
) -> ModelReliabilityReport:
    """Train/serve parity, leakage, validation, drift ve confidence stack doğrular."""
    checks = [
        _check_train_serve_feature_parity(),
        _check_leakage_removed(),
        _check_model_validation_state(model_info),
        _check_acceptance_and_promotion_rules(model_info),
        _check_walk_forward_validation(model_info),
        _check_drift_contract(drift),
        _check_confidence_stack_contract(confidence_stack),
        _check_prediction_interval_contract(confidence_stack),
        _check_coverage_contract(confidence_stack),
    ]
    gate_passed = all(check.passed for check in checks)
    return ModelReliabilityReport(
        gate_passed=gate_passed,
        checks=checks,
        model_type=str(model_info.get("type", "unknown")),
    )


def enforce_model_reliability_gate(report: ModelReliabilityReport) -> ModelReliabilityReport:
    if not report.gate_passed:
        raise ModelReliabilityGateError(report)
    return report


def _check_train_serve_feature_parity() -> ModelReliabilityCheck:
    try:
        train_vector = build_training_vector(
            physics_mw=12.0,
            hour_idx=14.0,
            capacity_mw=50.0,
            ptf_price=1800.0,
        )
        from datetime import datetime, timezone

        from modules.data_hub.schemas import WeatherData

        weather = WeatherData(
            timestamp=datetime(2026, 7, 7, 14, tzinfo=timezone.utc),
            temperature=20.0,
            wind_speed=8.0,
            wind_direction=180.0,
            air_pressure=1013.0,
        )
        infer_vector = build_inference_vector(
            weather,
            physics_mw=12.0,
            capacity_mw=50.0,
            ptf_price=1800.0,
        )
        validate_feature_vector(train_vector)
        validate_feature_vector(infer_vector)
        validate_feature_names(HYBRID_FEATURE_NAMES)
        passed = train_vector == infer_vector
        return ModelReliabilityCheck(
            name="train_serve_feature_parity",
            category="feature_schema",
            passed=passed,
            message="Train/serve feature parity uyumlu" if passed else "Train/serve vector mismatch",
            details={
                "feature_schema_version": FEATURE_SCHEMA_VERSION,
                "train_vector": train_vector,
                "infer_vector": infer_vector,
            },
        )
    except Exception as exc:
        return ModelReliabilityCheck(
            name="train_serve_feature_parity",
            category="feature_schema",
            passed=False,
            message=str(exc),
        )


def _check_leakage_removed() -> ModelReliabilityCheck:
    try:
        assert_no_leakage_features(HYBRID_FEATURE_NAMES)
        passed = "imbalance_cost_tl" not in HYBRID_FEATURE_NAMES
        return ModelReliabilityCheck(
            name="leakage_removed",
            category="feature_schema",
            passed=passed,
            message="Leakage feature yok" if passed else "Leakage feature tespit edildi",
            details={"feature_names": list(HYBRID_FEATURE_NAMES)},
        )
    except Exception as exc:
        return ModelReliabilityCheck(
            name="leakage_removed",
            category="feature_schema",
            passed=False,
            message=str(exc),
        )


def _check_model_validation_state(model_info: dict[str, Any]) -> ModelReliabilityCheck:
    model_type = str(model_info.get("type", "unknown"))
    validation = model_info.get("validation") or {}

    if model_type == "physics_only":
        return ModelReliabilityCheck(
            name="model_validation_state",
            category="validation",
            passed=True,
            message="Physics-only model validation gerektirmez",
            details={"model_type": model_type},
        )

    deployable = validation.get("deployable")
    passed = deployable is True
    return ModelReliabilityCheck(
        name="model_validation_state",
        category="validation",
        passed=passed,
        message="ML model deployable" if passed else "ML model validation geçmedi",
        details={
            "model_type": model_type,
            "deployable": deployable,
            "validation_version": validation.get("version"),
        },
    )


def _check_acceptance_and_promotion_rules(model_info: dict[str, Any]) -> ModelReliabilityCheck:
    model_type = str(model_info.get("type", "unknown"))
    validation = model_info.get("validation") or {}
    if model_type == "physics_only":
        return ModelReliabilityCheck(
            name="acceptance_promotion_rules",
            category="validation",
            passed=True,
            message="Physics-only için acceptance/promotion uygulanmaz",
        )

    acceptance = validation.get("acceptance_gate") or {}
    promotion = validation.get("promotion") or {}
    passed = bool(acceptance.get("passed")) and bool(promotion.get("promoted"))
    return ModelReliabilityCheck(
        name="acceptance_promotion_rules",
        category="validation",
        passed=passed,
        message="Acceptance + promotion geçti" if passed else "Acceptance/promotion başarısız",
        details={"acceptance": acceptance, "promotion": promotion},
    )


def _check_walk_forward_validation(model_info: dict[str, Any]) -> ModelReliabilityCheck:
    model_type = str(model_info.get("type", "unknown"))
    validation = model_info.get("validation") or {}
    if model_type == "physics_only":
        return ModelReliabilityCheck(
            name="walk_forward_validation",
            category="validation",
            passed=True,
            message="Physics-only için walk-forward uygulanmaz",
        )

    walk_forward = validation.get("walk_forward") or {}
    passed = bool(walk_forward.get("passed", False))
    return ModelReliabilityCheck(
        name="walk_forward_validation",
        category="validation",
        passed=passed,
        message="Walk-forward geçti" if passed else "Walk-forward başarısız veya eksik",
        details=walk_forward,
    )


def _check_drift_contract(drift: dict[str, Any] | None) -> ModelReliabilityCheck:
    if drift is None:
        return ModelReliabilityCheck(
            name="drift_contract",
            category="monitoring",
            passed=True,
            message="Drift henüz hesaplanmadı (pre-stack)",
            details={"skipped": True},
        )

    required = ("version", "detection_method", "mape_drift", "cost_drift", "drift_severity")
    missing = [field for field in required if field not in drift]
    passed = not missing and drift.get("version") == DRIFT_DETECTION_VERSION
    return ModelReliabilityCheck(
        name="drift_contract",
        category="monitoring",
        passed=passed,
        message="Drift contract geçerli" if passed else "Drift contract eksik/hatalı",
        details={"missing_fields": missing, "version": drift.get("version")},
    )


def _check_confidence_stack_contract(confidence_stack: dict[str, Any] | None) -> ModelReliabilityCheck:
    if confidence_stack is None:
        return ModelReliabilityCheck(
            name="confidence_stack_contract",
            category="confidence",
            passed=True,
            message="Confidence stack henüz hesaplanmadı (pre-stack)",
            details={"skipped": True},
        )

    required = ("version", "base_confidence", "confidence_calibrated", "prediction_interval", "coverage")
    missing = [field for field in required if field not in confidence_stack]
    passed = not missing and confidence_stack.get("version") == CONFIDENCE_STACK_VERSION
    return ModelReliabilityCheck(
        name="confidence_stack_contract",
        category="confidence",
        passed=passed,
        message="Confidence stack contract geçerli" if passed else "Confidence stack eksik/hatalı",
        details={"missing_fields": missing},
    )


def _check_prediction_interval_contract(confidence_stack: dict[str, Any] | None) -> ModelReliabilityCheck:
    if confidence_stack is None:
        return ModelReliabilityCheck(
            name="prediction_interval_contract",
            category="confidence",
            passed=True,
            message="Prediction interval henüz hesaplanmadı",
            details={"skipped": True},
        )

    interval = confidence_stack.get("prediction_interval") or {}
    required = ("point_mw", "lower_mw", "upper_mw", "margin_mw")
    missing = [field for field in required if field not in interval]
    lower = float(interval.get("lower_mw", -1))
    upper = float(interval.get("upper_mw", -1))
    point = float(interval.get("point_mw", -1))
    passed = not missing and lower <= point <= upper
    return ModelReliabilityCheck(
        name="prediction_interval_contract",
        category="confidence",
        passed=passed,
        message="Prediction interval geçerli" if passed else "Prediction interval hatalı",
        details={"interval": interval, "missing_fields": missing},
    )


def _check_coverage_contract(confidence_stack: dict[str, Any] | None) -> ModelReliabilityCheck:
    if confidence_stack is None:
        return ModelReliabilityCheck(
            name="coverage_contract",
            category="confidence",
            passed=True,
            message="Coverage henüz hesaplanmadı",
            details={"skipped": True},
        )

    coverage = confidence_stack.get("coverage") or {}
    required = ("coverage_rate", "evaluated_hours", "covered_hours", "target_coverage", "meets_target")
    missing = [field for field in required if field not in coverage]
    passed = not missing and 0.0 <= float(coverage.get("coverage_rate", -1)) <= 1.0
    return ModelReliabilityCheck(
        name="coverage_contract",
        category="confidence",
        passed=passed,
        message="Coverage metrikleri geçerli" if passed else "Coverage contract hatalı",
        details={"coverage": coverage, "missing_fields": missing},
    )
