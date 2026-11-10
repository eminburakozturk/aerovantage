"""Data contract validation tests for cross-layer pipeline boundaries."""

from __future__ import annotations

from datetime import date

from core.data_contracts import CONTRACT_VERSION, DATA_CONTRACTS
from core.pipeline import EventPipeline


def test_data_contract_catalog_is_versioned() -> None:
    assert DATA_CONTRACTS
    assert all(contract.version == CONTRACT_VERSION for contract in DATA_CONTRACTS)


def test_pipeline_metadata_includes_contract_validation_state() -> None:
    pipeline = EventPipeline()
    result = pipeline.execute_daily_pipeline("RES-BAL-01", date(2026, 7, 6))

    contracts = result.metadata.get("data_contracts")
    assert contracts is not None
    assert contracts["version"] == CONTRACT_VERSION
    assert contracts["forecast_to_performance"] == "validated"
    assert contracts["performance_to_risk"] == "validated"
    assert contracts["risk_to_ai"] == "validated"
    assert contracts["pipeline_to_monitoring"] == "validated"
    data_quality = result.metadata.get("data_quality")
    assert data_quality is not None
    assert data_quality["gate_passed"] is True
    assert data_quality["score"] >= 70
    model_reliability = result.metadata.get("model_reliability")
    assert model_reliability is not None
    assert model_reliability["gate_passed"] is True
    decision_reliability = result.metadata.get("decision_reliability")
    assert decision_reliability is not None
    assert decision_reliability["gate_passed"] is True
