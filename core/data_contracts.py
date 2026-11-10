"""Versioned data contracts for cross-layer pipeline handoffs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from pydantic import Field

from core.schemas import AeroVantageSchema
from modules.forecast.production.schemas import ProductionForecastResponse
from modules.risk.schemas import DailyRiskScoreResponse


CONTRACT_VERSION = "1.0.0"


@dataclass(frozen=True)
class DataContractDefinition:
    """Defines a versioned boundary between two pipeline layers."""

    name: str
    version: str
    source_layer: str
    target_layer: str
    input_schema: str
    output_schema: str


class ContractPredictionHour(AeroVantageSchema):
    timestamp: datetime
    generated_mw: float = Field(..., ge=0)


class PredictionContract(AeroVantageSchema):
    contract: str = "PredictionContract"
    version: str = CONTRACT_VERSION
    asset_id: str = Field(..., min_length=1)
    target_date: date
    hours: list[ContractPredictionHour] = Field(..., min_length=1)
    total_daily_mw: float = Field(..., ge=0)


class ContractRiskInputHour(AeroVantageSchema):
    timestamp: datetime
    forecast_mw: float = Field(..., ge=0)
    actual_mw: float = Field(..., ge=0)
    deviation_mw: float
    mape_percentage: float = Field(..., ge=0)


class RiskInputContract(AeroVantageSchema):
    contract: str = "RiskInputContract"
    version: str = CONTRACT_VERSION
    asset_id: str = Field(..., min_length=1)
    target_date: date
    hours: list[ContractRiskInputHour] = Field(..., min_length=1)
    mape_percentage: float = Field(..., ge=0)


class RecommendationInputContract(AeroVantageSchema):
    contract: str = "RecommendationInputContract"
    version: str = CONTRACT_VERSION
    asset_id: str = Field(..., min_length=1)
    target_date: date
    risk_score: int = Field(..., ge=0, le=100)
    total_imbalance_cost_tl: float = Field(..., ge=0)
    mape_percentage: float = Field(..., ge=0)
    forecast_mw: float = Field(..., ge=0)
    avg_forecast_mw: float = Field(..., ge=0)
    avg_ptf_price: float = Field(..., ge=0)
    wind_speed_mps: float = Field(..., ge=0)


class MonitoringContract(AeroVantageSchema):
    contract: str = "MonitoringContract"
    version: str = CONTRACT_VERSION
    asset_id: str = Field(..., min_length=1)
    target_date: date
    risk_score: int = Field(..., ge=0, le=100)
    total_imbalance_cost_tl: float = Field(..., ge=0)
    mape_percentage: float = Field(..., ge=0)
    confidence_calibrated: int = Field(..., ge=0, le=100)


DATA_CONTRACTS: tuple[DataContractDefinition, ...] = (
    DataContractDefinition(
        name="forecast_to_performance",
        version=CONTRACT_VERSION,
        source_layer="forecast",
        target_layer="performance",
        input_schema="ForecastInputContract",
        output_schema="PredictionContract",
    ),
    DataContractDefinition(
        name="performance_to_risk",
        version=CONTRACT_VERSION,
        source_layer="performance",
        target_layer="risk",
        input_schema="PerformanceEvaluationResponse",
        output_schema="RiskInputContract",
    ),
    DataContractDefinition(
        name="risk_to_ai",
        version=CONTRACT_VERSION,
        source_layer="risk",
        target_layer="ai",
        input_schema="DailyRiskScoreResponse",
        output_schema="RecommendationInputContract",
    ),
    DataContractDefinition(
        name="pipeline_to_monitoring",
        version=CONTRACT_VERSION,
        source_layer="pipeline",
        target_layer="monitoring",
        input_schema="PipelineRunResult.metadata",
        output_schema="MonitoringContract",
    ),
)


def validate_contract_registry(expected_version: str = CONTRACT_VERSION) -> None:
    """Tüm kayıtlı contract tanımlarının beklenen sürümde olduğunu doğrular."""
    mismatches = [
        contract.name
        for contract in DATA_CONTRACTS
        if contract.version != expected_version
    ]
    if mismatches:
        raise ValueError(
            f"Contract version mismatch: expected={expected_version} mismatched={mismatches}"
        )


def get_contract_registry() -> dict[str, str]:
    """Aktif contract adı -> sürüm haritasını döndürür."""
    return {contract.name: contract.version for contract in DATA_CONTRACTS}


def validate_prediction_contract(
    forecast: ProductionForecastResponse,
    *,
    asset_id: str,
    target_date: date,
) -> PredictionContract:
    validate_contract_registry()
    contract = PredictionContract(
        asset_id=asset_id,
        target_date=target_date,
        hours=[
            ContractPredictionHour(
                timestamp=hour.timestamp,
                generated_mw=hour.generated_mw,
            )
            for hour in forecast.hours
        ],
        total_daily_mw=forecast.total_daily_mw,
    )
    if len(contract.hours) != 24:
        raise ValueError(f"PredictionContract requires 24 hours, got={len(contract.hours)}")
    return contract


def validate_risk_input_contract(
    performance_data: dict[str, Any],
    *,
    asset_id: str,
    target_date: date,
) -> RiskInputContract:
    validate_contract_registry()
    return RiskInputContract(
        asset_id=asset_id,
        target_date=target_date,
        hours=[
            ContractRiskInputHour(
                timestamp=hour["timestamp"],
                forecast_mw=hour["forecast_mw"],
                actual_mw=hour["actual_mw"],
                deviation_mw=hour["deviation_mw"],
                mape_percentage=hour["mape_percentage"],
            )
            for hour in performance_data.get("hours", [])
        ],
        mape_percentage=float(performance_data.get("mape_percentage") or 0.0),
    )


def validate_recommendation_input_contract(
    risk_data: dict[str, Any],
    *,
    target_date: date,
) -> RecommendationInputContract:
    validate_contract_registry()
    return RecommendationInputContract(
        asset_id=risk_data["asset_id"],
        target_date=target_date,
        risk_score=risk_data["risk_score"],
        total_imbalance_cost_tl=risk_data["total_imbalance_cost_tl"],
        mape_percentage=risk_data["mape_percentage"],
        forecast_mw=risk_data["forecast_mw"],
        avg_forecast_mw=risk_data["avg_forecast_mw"],
        avg_ptf_price=risk_data["avg_ptf_price"],
        wind_speed_mps=risk_data["wind_speed_mps"],
    )


def validate_monitoring_contract(metadata: dict[str, Any], *, target_date: date) -> MonitoringContract:
    validate_contract_registry()
    return MonitoringContract(
        asset_id=metadata["asset_id"],
        target_date=target_date,
        risk_score=metadata["risk_score"],
        total_imbalance_cost_tl=metadata["total_imbalance_cost_tl"],
        mape_percentage=metadata["mape_percentage"],
        confidence_calibrated=metadata["confidence_calibrated"],
    )
