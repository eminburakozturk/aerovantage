"""FAZ 2 — data quality gate ve skor testleri."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from core.data_contracts import CONTRACT_VERSION, validate_contract_registry
from core.data_quality import (
    DQ_GATE_MIN_SCORE,
    DataQualityReport,
    build_quality_report,
    enforce_pipeline_data_quality_gate,
    run_pipeline_data_quality_gate,
    run_pre_pipeline_quality_gate,
)
from modules.asset_registry.service import AssetRegistryService
from modules.data_hub.errors import DataQualityGateError
from modules.forecast.production.schemas import ProductionData, ProductionForecastResponse
from modules.risk.schemas import DailyRiskScoreResponse, HourlyRiskData

_TURKEY_TZ = ZoneInfo("Europe/Istanbul")


def _ts(target_date: date, hour: int) -> datetime:
    """Teslimat saati (Europe/Istanbul) → UTC saklama."""
    local = datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        hour,
        tzinfo=_TURKEY_TZ,
    )
    return local.astimezone(timezone.utc)


def _hourly_forecast(target_date: date) -> ProductionForecastResponse:
    hours = [
        ProductionData(
            timestamp=_ts(target_date, hour),
            generated_mw=10.0 + hour * 0.1,
        )
        for hour in range(24)
    ]
    total = round(sum(hour.generated_mw for hour in hours), 4)
    return ProductionForecastResponse(hours=hours, total_daily_mw=total, source="test")


def _hourly_performance(target_date: date) -> dict:
    hours = []
    for hour in range(24):
        forecast_mw = 10.0 + hour * 0.1
        actual_mw = 9.5 + hour * 0.1
        hours.append(
            {
                "timestamp": _ts(target_date, hour).isoformat(),
                "forecast_mw": forecast_mw,
                "actual_mw": actual_mw,
                "deviation_mw": round(actual_mw - forecast_mw, 4),
                "mape_percentage": 5.0,
            }
        )
    return {"hours": hours, "mape_percentage": 5.0, "scada": {"mode": "mock", "reason": "forced_mock"}}


def _hourly_risk(target_date: date) -> DailyRiskScoreResponse:
    hours = [
        HourlyRiskData(
            timestamp=_ts(target_date, hour),
            forecast_mw=10.0 + hour * 0.1,
            actual_mw=9.5 + hour * 0.1,
            ptf_price=2800.0 + hour,
            imbalance_cost_tl=12.5,
        )
        for hour in range(24)
    ]
    return DailyRiskScoreResponse(
        target_date=target_date,
        total_imbalance_cost_tl=300.0,
        risk_score=35,
        hours=hours,
        market_source="epias-live",
    )


def test_contract_registry_versioned() -> None:
    validate_contract_registry()
    assert CONTRACT_VERSION == "1.0.0"


def test_pre_pipeline_gate_passes_for_valid_asset() -> None:
    asset = AssetRegistryService().get_asset_by_id("RES-BAL-01")
    report = run_pre_pipeline_quality_gate(asset, date(2026, 7, 6))
    assert report.gate_passed
    assert report.score >= DQ_GATE_MIN_SCORE


def test_pipeline_data_quality_gate_passes_for_complete_datasets() -> None:
    asset = AssetRegistryService().get_asset_by_id("RES-BAL-01")
    target = date(2026, 7, 6)
    report = run_pipeline_data_quality_gate(
        asset=asset,
        target_date=target,
        forecast=_hourly_forecast(target),
        performance=_hourly_performance(target),
        risk=_hourly_risk(target),
    )
    assert report.gate_passed
    assert report.score >= DQ_GATE_MIN_SCORE
    assert report.to_dict()["gate_passed"] is True


def test_performance_deviation_matches_service_formula() -> None:
    """Performance servisi actual-forecast kullanır; DQ gate aynı formülü doğrular."""
    from modules.performance.service import PerformanceMonitoringService

    target = date(2026, 7, 6)
    forecast = _hourly_forecast(target)
    performance = PerformanceMonitoringService().evaluate_performance(
        forecast.model_dump(mode="json"),
        asset_id="RES-BAL-01",
        target_date=target.isoformat(),
    )
    asset = AssetRegistryService().get_asset_by_id("RES-BAL-01")
    report = run_pipeline_data_quality_gate(
        asset=asset,
        target_date=target,
        forecast=forecast,
        performance=performance,
        risk=_hourly_risk(target),
    )
    deviation_check = next(
        check for check in report.checks if check.name == "performance_deviation_consistency"
    )
    assert deviation_check.passed, deviation_check.details


    asset = AssetRegistryService().get_asset_by_id("RES-BAL-01")
    target = date(2026, 7, 6)
    forecast = _hourly_forecast(target)
    duplicate = forecast.hours[0]
    forecast = ProductionForecastResponse(
        hours=[duplicate, duplicate],
        total_daily_mw=duplicate.generated_mw * 2,
        source="test",
    )
    report = run_pipeline_data_quality_gate(
        asset=asset,
        target_date=target,
        forecast=forecast,
        performance=_hourly_performance(target),
        risk=_hourly_risk(target),
    )
    assert not report.gate_passed
    assert report.critical_failures


def test_enforce_gate_raises_on_failure() -> None:
    failed = DataQualityReport(score=10.0, gate_passed=False, critical_failures=["test"])
    with pytest.raises(DataQualityGateError):
        enforce_pipeline_data_quality_gate(failed)


def test_build_quality_report_scores_weighted_checks() -> None:
    from core.data_quality import QualityCheck

    report = build_quality_report(
        [
            QualityCheck("ok", "contract", True, "critical", "ok"),
            QualityCheck("bad", "duplicate", False, "critical", "dup"),
        ]
    )
    assert report.score < 100
    assert not report.gate_passed
