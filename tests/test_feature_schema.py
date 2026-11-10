"""Feature schema parity and leakage guard tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from modules.data_hub.schemas import WeatherData
from modules.forecast.production.feature_schema import (
    FEATURE_SCHEMA_VERSION,
    HYBRID_FEATURE_NAMES,
    LEAKAGE_FORBIDDEN_FIELDS,
    assert_no_leakage_features,
    build_inference_vector,
    build_training_vector,
    parse_hour_index,
    validate_feature_names,
    validate_feature_vector,
)
from modules.forecast.production.models.xgb_hybrid_model import HybridWindPowerModel


def _weather(hour: int = 14) -> WeatherData:
    return WeatherData(
        timestamp=datetime(2026, 7, 7, hour, 0, tzinfo=timezone.utc),
        wind_speed=8.5,
        wind_direction=180.0,
        temperature=22.0,
        air_pressure=1013.0,
    )


def test_hybrid_feature_names_are_leakage_free() -> None:
    assert_no_leakage_features(HYBRID_FEATURE_NAMES)
    assert "imbalance_cost_tl" not in HYBRID_FEATURE_NAMES


def test_train_and_inference_vectors_share_schema() -> None:
    train_vector = build_training_vector(
        physics_mw=12.5,
        hour_idx=14.0,
        capacity_mw=50.0,
        ptf_price=1800.0,
    )
    infer_vector = build_inference_vector(
        _weather(14),
        physics_mw=12.5,
        capacity_mw=50.0,
        ptf_price=1800.0,
    )

    assert train_vector == infer_vector
    validate_feature_vector(train_vector)
    validate_feature_names(HYBRID_FEATURE_NAMES)


def test_inference_defaults_match_schema() -> None:
    vector = build_inference_vector(
        _weather(9),
        physics_mw=7.2,
        capacity_mw=40.0,
    )
    assert vector == [7.2, 9.0, 40.0, 0.0]


def test_validate_feature_names_rejects_drift() -> None:
    with pytest.raises(ValueError, match="Feature name contract mismatch"):
        validate_feature_names(["physics_mw", "hour_idx", "capacity_mw", "imbalance_cost_tl"])


def test_assert_no_leakage_features_rejects_forbidden_names() -> None:
    with pytest.raises(ValueError, match="Leakage fields cannot be model features"):
        assert_no_leakage_features(["physics_mw", "imbalance_cost_tl"])


def test_parse_hour_index_handles_iso_and_missing() -> None:
    assert parse_hour_index("2026-07-07T16:30:00Z") == 16.0
    assert parse_hour_index(None) == 12.0


def test_hybrid_model_info_exposes_feature_schema() -> None:
    model = HybridWindPowerModel(capacity_mw=30.0)
    info = model.model_info

    assert info["feature_schema_version"] == FEATURE_SCHEMA_VERSION
    assert info["feature_names"] == list(HYBRID_FEATURE_NAMES)
    assert len(info["feature_names"]) == 4


def test_feature_schema_version_is_semver_like() -> None:
    parts = FEATURE_SCHEMA_VERSION.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_leakage_forbidden_fields_cover_outcome_derived_signals() -> None:
    assert "imbalance_cost_tl" in LEAKAGE_FORBIDDEN_FIELDS
    assert "actual_mw" in LEAKAGE_FORBIDDEN_FIELDS
