"""Pipeline veri kalitesi kontrolleri, skor ve fail-fast gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from statistics import median
from typing import Any, Sequence
from zoneinfo import ZoneInfo

from core.data_contracts import CONTRACT_VERSION, DATA_CONTRACTS, validate_contract_registry
from modules.asset_registry.service import Asset
from modules.data_hub.errors import DataQualityGateError
from modules.data_hub.freshness import check_hourly_freshness
from modules.forecast.production.feature_schema import (
    FEATURE_SCHEMA_VERSION,
    HYBRID_FEATURE_NAMES,
    assert_no_leakage_features,
    validate_feature_names,
)
from modules.forecast.production.schemas import ProductionForecastResponse
from modules.risk.schemas import DailyRiskScoreResponse

DQ_GATE_MIN_SCORE = 70.0
_EXPECTED_HOURLY_COUNT = 24
_TOTAL_MW_TOLERANCE = 0.5
_DEVIATION_TOLERANCE = 0.05
_OUTLIER_IQR_MULTIPLIER = 1.5
_TURKEY_TZ = ZoneInfo("Europe/Istanbul")

CHECK_WEIGHTS: dict[str, float] = {
    "contract": 0.10,
    "schema": 0.10,
    "completeness": 0.25,
    "timeliness": 0.15,
    "consistency": 0.15,
    "duplicate": 0.10,
    "missing": 0.10,
    "outlier": 0.05,
}


@dataclass(frozen=True)
class QualityCheck:
    name: str
    category: str
    passed: bool
    severity: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def score(self) -> float:
        return 100.0 if self.passed else 0.0


@dataclass
class DataQualityReport:
    score: float
    gate_passed: bool
    checks: list[QualityCheck] = field(default_factory=list)
    critical_failures: list[str] = field(default_factory=list)
    contract_version: str = CONTRACT_VERSION
    feature_schema_version: str = FEATURE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 2),
            "gate_passed": self.gate_passed,
            "min_required_score": DQ_GATE_MIN_SCORE,
            "contract_version": self.contract_version,
            "feature_schema_version": self.feature_schema_version,
            "critical_failures": self.critical_failures,
            "checks": [
                {
                    "name": check.name,
                    "category": check.category,
                    "passed": check.passed,
                    "severity": check.severity,
                    "message": check.message,
                    "score": check.score,
                    "details": check.details,
                }
                for check in self.checks
            ],
        }


def merge_quality_reports(*reports: DataQualityReport) -> DataQualityReport:
    checks: list[QualityCheck] = []
    for report in reports:
        checks.extend(report.checks)
    return build_quality_report(checks)


def build_quality_report(checks: Sequence[QualityCheck]) -> DataQualityReport:
    weighted_sum = 0.0
    weight_total = 0.0
    for check in checks:
        weight = CHECK_WEIGHTS.get(check.category, 0.05)
        weighted_sum += check.score * weight
        weight_total += weight

    score = (weighted_sum / weight_total) if weight_total else 0.0
    critical_failures = [
        f"{check.name}: {check.message}"
        for check in checks
        if not check.passed and check.severity == "critical"
    ]
    gate_passed = score >= DQ_GATE_MIN_SCORE and not critical_failures
    return DataQualityReport(
        score=score,
        gate_passed=gate_passed,
        checks=list(checks),
        critical_failures=critical_failures,
    )


def run_pre_pipeline_quality_gate(asset: Asset, target_date: date) -> DataQualityReport:
    """Pipeline başlamadan önce contract, schema ve asset bütünlüğünü doğrular."""
    checks = [
        _check_contract_versions(),
        _check_feature_schema_contract(),
        _check_asset_completeness(asset),
        _check_target_date_valid(target_date),
    ]
    return build_quality_report(checks)


def run_pipeline_data_quality_gate(
    *,
    asset: Asset,
    target_date: date,
    forecast: ProductionForecastResponse,
    performance: dict[str, Any],
    risk: DailyRiskScoreResponse,
) -> DataQualityReport:
    """Veri katmanları toplandıktan sonra tam DQ değerlendirmesi yapar."""
    checks = [
        _check_contract_versions(),
        _check_feature_schema_contract(),
        _check_forecast_completeness(forecast),
        _check_performance_completeness(performance),
        _check_risk_completeness(risk, performance),
        _check_forecast_timeliness(forecast, target_date),
        _check_forecast_total_consistency(forecast),
        _check_performance_deviation_consistency(performance),
        _check_duplicate_timestamps(forecast.hours, "forecast"),
        _check_duplicate_timestamps(performance.get("hours", []), "performance", field_name="timestamp"),
        _check_missing_values(forecast, performance, risk),
        _check_outliers(forecast, risk),
    ]
    return build_quality_report(checks)


def enforce_pipeline_data_quality_gate(report: DataQualityReport) -> DataQualityReport:
    """Gate başarısızsa fail-fast exception fırlatır."""
    if not report.gate_passed:
        raise DataQualityGateError(report)
    return report


def _check_contract_versions() -> QualityCheck:
    try:
        validate_contract_registry()
        registry = {contract.name: contract.version for contract in DATA_CONTRACTS}
        return QualityCheck(
            name="contract_version_registry",
            category="contract",
            passed=True,
            severity="critical",
            message="Tüm data contract sürümleri uyumlu",
            details={"registry": registry, "version": CONTRACT_VERSION},
        )
    except Exception as exc:
        return QualityCheck(
            name="contract_version_registry",
            category="contract",
            passed=False,
            severity="critical",
            message=str(exc),
        )


def _check_feature_schema_contract() -> QualityCheck:
    try:
        validate_feature_names(HYBRID_FEATURE_NAMES)
        assert_no_leakage_features(HYBRID_FEATURE_NAMES)
        return QualityCheck(
            name="feature_schema_single_source",
            category="schema",
            passed=True,
            severity="critical",
            message="Feature schema tek kaynak ve leakage-free",
            details={
                "feature_schema_version": FEATURE_SCHEMA_VERSION,
                "feature_names": list(HYBRID_FEATURE_NAMES),
            },
        )
    except Exception as exc:
        return QualityCheck(
            name="feature_schema_single_source",
            category="schema",
            passed=False,
            severity="critical",
            message=str(exc),
        )


def _check_asset_completeness(asset: Asset) -> QualityCheck:
    missing: list[str] = []
    if not asset.id:
        missing.append("id")
    if asset.lat is None or asset.lon is None:
        missing.append("coordinates")
    if asset.capacity_mw <= 0:
        missing.append("capacity_mw")
    passed = not missing
    return QualityCheck(
        name="asset_profile_completeness",
        category="completeness",
        passed=passed,
        severity="critical",
        message="Asset profili tam" if passed else f"Eksik asset alanları: {', '.join(missing)}",
        details={"missing_fields": missing},
    )


def _check_target_date_valid(target_date: date) -> QualityCheck:
    passed = isinstance(target_date, date)
    return QualityCheck(
        name="target_date_present",
        category="completeness",
        passed=passed,
        severity="critical",
        message="Hedef tarih geçerli" if passed else "Hedef tarih eksik",
        details={"target_date": target_date.isoformat() if passed else None},
    )


def _check_forecast_completeness(forecast: ProductionForecastResponse) -> QualityCheck:
    hour_count = len(forecast.hours)
    passed = hour_count == _EXPECTED_HOURLY_COUNT
    return QualityCheck(
        name="forecast_hour_coverage",
        category="completeness",
        passed=passed,
        severity="critical",
        message=(
            f"Forecast {hour_count}/{_EXPECTED_HOURLY_COUNT} saat"
            if passed
            else f"Forecast eksik saat: {hour_count}/{_EXPECTED_HOURLY_COUNT}"
        ),
        details={"hour_count": hour_count, "expected": _EXPECTED_HOURLY_COUNT},
    )


def _check_performance_completeness(performance: dict[str, Any]) -> QualityCheck:
    hours = performance.get("hours", [])
    hour_count = len(hours)
    passed = hour_count == _EXPECTED_HOURLY_COUNT
    return QualityCheck(
        name="performance_hour_coverage",
        category="completeness",
        passed=passed,
        severity="warning" if hour_count > 0 else "critical",
        message=(
            f"Performance {hour_count}/{_EXPECTED_HOURLY_COUNT} saat"
            if passed
            else f"Performance eksik saat: {hour_count}/{_EXPECTED_HOURLY_COUNT}"
        ),
        details={"hour_count": hour_count, "expected": _EXPECTED_HOURLY_COUNT},
    )


def _check_risk_completeness(
    risk: DailyRiskScoreResponse,
    performance: dict[str, Any] | None = None,
) -> QualityCheck:
    hour_count = len(risk.hours)
    expected = _EXPECTED_HOURLY_COUNT
    passed = hour_count == expected
    simulation = bool(
        performance
        and (
            performance.get("evaluation_mode") == "simulation"
            or performance.get("mape_informational") is True
        )
    )
    if passed:
        severity = "info"
    elif simulation and hour_count > 0:
        severity = "warning"
    else:
        severity = "critical"
    return QualityCheck(
        name="risk_hour_coverage",
        category="completeness",
        passed=passed,
        severity=severity,
        message=(
            f"Risk {hour_count}/{expected} saat"
            if passed
            else f"Risk eksik saat: {hour_count}/{expected}"
        ),
        details={"hour_count": hour_count, "expected": expected, "simulation": simulation},
    )


def _check_forecast_timeliness(
    forecast: ProductionForecastResponse,
    target_date: date,
) -> QualityCheck:
    freshness = check_hourly_freshness(forecast.hours, target_date)
    # Open-Meteo UTC saklanır; teslimat günü Europe/Istanbul ile karşılaştırılmalı
    date_match = all(_local_delivery_date(hour.timestamp) == target_date for hour in forecast.hours)
    passed = date_match and bool(freshness["freshness_ok"])
    return QualityCheck(
        name="forecast_timeliness",
        category="timeliness",
        passed=passed,
        severity="warning" if date_match else "critical",
        message="Forecast timeliness uygun" if passed else f"Timeliness sorunu: {freshness['reason']}",
        details={**freshness, "target_date_match": date_match},
    )


def _local_delivery_date(timestamp: Any) -> date:
    """UTC/aware timestamp → Europe/Istanbul takvim günü."""
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    aware = timestamp if getattr(timestamp, "tzinfo", None) else timestamp.replace(tzinfo=timezone.utc)
    return aware.astimezone(_TURKEY_TZ).date()


def _check_forecast_total_consistency(forecast: ProductionForecastResponse) -> QualityCheck:
    computed_total = round(sum(hour.generated_mw for hour in forecast.hours), 4)
    delta = abs(computed_total - forecast.total_daily_mw)
    passed = delta <= _TOTAL_MW_TOLERANCE
    return QualityCheck(
        name="forecast_total_consistency",
        category="consistency",
        passed=passed,
        severity="critical",
        message="Forecast toplamı tutarlı" if passed else f"Toplam sapma: {delta}",
        details={
            "computed_total": computed_total,
            "declared_total": forecast.total_daily_mw,
            "delta": delta,
        },
    )


def _check_performance_deviation_consistency(performance: dict[str, Any]) -> QualityCheck:
    mismatches: list[dict[str, Any]] = []
    for hour in performance.get("hours", []):
        forecast_mw = float(hour.get("forecast_mw", 0.0))
        actual_mw = float(hour.get("actual_mw", 0.0))
        deviation_mw = float(hour.get("deviation_mw", 0.0))
        expected = round(actual_mw - forecast_mw, 4)
        if abs(expected - deviation_mw) > _DEVIATION_TOLERANCE:
            mismatches.append(
                {
                    "timestamp": hour.get("timestamp"),
                    "expected_deviation": expected,
                    "declared_deviation": deviation_mw,
                }
            )
    passed = not mismatches
    return QualityCheck(
        name="performance_deviation_consistency",
        category="consistency",
        passed=passed,
        severity="critical",
        message="Sapma formülü tutarlı" if passed else "Sapma tutarsızlığı tespit edildi",
        details={"mismatch_count": len(mismatches), "samples": mismatches[:3]},
    )


def _check_duplicate_timestamps(
    rows: Sequence[Any],
    dataset_name: str,
    *,
    field_name: str = "timestamp",
) -> QualityCheck:
    seen: set[str] = set()
    duplicates: list[str] = []
    for row in rows:
        if isinstance(row, dict):
            raw_ts = row.get(field_name)
        else:
            raw_ts = getattr(row, field_name, None)
        if raw_ts is None:
            continue
        key = str(raw_ts)
        if key in seen:
            duplicates.append(key)
        seen.add(key)

    passed = not duplicates
    return QualityCheck(
        name=f"{dataset_name}_duplicate_timestamps",
        category="duplicate",
        passed=passed,
        severity="critical",
        message="Duplicate yok" if passed else f"{len(duplicates)} duplicate timestamp",
        details={"duplicate_count": len(duplicates), "samples": duplicates[:5]},
    )


def _check_missing_values(
    forecast: ProductionForecastResponse,
    performance: dict[str, Any],
    risk: DailyRiskScoreResponse,
) -> QualityCheck:
    missing: list[str] = []

    for index, hour in enumerate(forecast.hours):
        if hour.generated_mw is None:
            missing.append(f"forecast[{index}].generated_mw")

    for index, hour in enumerate(performance.get("hours", [])):
        for field in ("forecast_mw", "actual_mw", "deviation_mw"):
            if hour.get(field) is None:
                missing.append(f"performance[{index}].{field}")

    for index, hour in enumerate(risk.hours):
        for field_name, value in (
            ("forecast_mw", hour.forecast_mw),
            ("actual_mw", hour.actual_mw),
            ("ptf_price", hour.ptf_price),
        ):
            if value is None:
                missing.append(f"risk[{index}].{field_name}")

    passed = not missing
    return QualityCheck(
        name="required_field_missing_values",
        category="missing",
        passed=passed,
        severity="critical",
        message="Zorunlu alanlar dolu" if passed else "Eksik zorunlu alanlar var",
        details={"missing_count": len(missing), "samples": missing[:8]},
    )


def _check_outliers(
    forecast: ProductionForecastResponse,
    risk: DailyRiskScoreResponse,
) -> QualityCheck:
    forecast_values = [hour.generated_mw for hour in forecast.hours]
    ptf_values = [hour.ptf_price for hour in risk.hours if hour.ptf_price is not None]

    forecast_outliers = _detect_iqr_outliers(forecast_values)
    # Canlı EPİAŞ PTF gün içi volatil; IQR outlier yalnız bilgilendirme (gate'i düşürmez)
    ptf_outliers = _detect_iqr_outliers(ptf_values)
    # Forecast outlier'ları gate skoruna girer; PTF outlier severity=info benzeri warning ama
    # yalnızca forecast outlier sayılır "passed" için
    passed = len(forecast_outliers) == 0
    outlier_count = len(forecast_outliers) + len(ptf_outliers)

    return QualityCheck(
        name="statistical_outlier_detection",
        category="outlier",
        passed=passed,
        severity="warning",
        message=(
            "Outlier yok"
            if outlier_count == 0
            else f"{len(forecast_outliers)} forecast / {len(ptf_outliers)} PTF outlier"
        ),
        details={
            "forecast_outlier_count": len(forecast_outliers),
            "ptf_outlier_count": len(ptf_outliers),
            "forecast_outlier_samples": forecast_outliers[:3],
            "ptf_outlier_samples": ptf_outliers[:3],
            "ptf_outliers_informational": True,
        },
    )


def _detect_iqr_outliers(values: Sequence[float]) -> list[float]:
    if len(values) < 4:
        return []
    sorted_values = sorted(float(value) for value in values)
    mid = len(sorted_values) // 2
    lower_half = sorted_values[:mid]
    upper_half = sorted_values[mid + 1 :] if len(sorted_values) % 2 else sorted_values[mid:]
    if not lower_half or not upper_half:
        return []
    q1 = median(lower_half)
    q3 = median(upper_half)
    iqr = q3 - q1
    if iqr <= 0:
        return []
    lower_bound = q1 - _OUTLIER_IQR_MULTIPLIER * iqr
    upper_bound = q3 + _OUTLIER_IQR_MULTIPLIER * iqr
    return [value for value in sorted_values if value < lower_bound or value > upper_bound]
