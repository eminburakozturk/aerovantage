"""Single source of truth for hybrid model feature contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Sequence

from modules.data_hub.schemas import WeatherData

FEATURE_SCHEMA_VERSION = "1.0.0"

# Outcome-derived fields must never enter the training/inference feature vector.
LEAKAGE_FORBIDDEN_FIELDS = frozenset({"imbalance_cost_tl", "actual_mw", "deviation_mw"})


@dataclass(frozen=True)
class HybridFeatureSpec:
    name: str
    inference_default: float


HYBRID_FEATURE_SPECS: tuple[HybridFeatureSpec, ...] = (
    HybridFeatureSpec(name="physics_mw", inference_default=0.0),
    HybridFeatureSpec(name="hour_idx", inference_default=12.0),
    HybridFeatureSpec(name="capacity_mw", inference_default=0.0),
    HybridFeatureSpec(name="ptf_price", inference_default=0.0),
)

HYBRID_FEATURE_NAMES: tuple[str, ...] = tuple(spec.name for spec in HYBRID_FEATURE_SPECS)


def feature_defaults() -> dict[str, float]:
    return {spec.name: spec.inference_default for spec in HYBRID_FEATURE_SPECS}


def build_inference_vector(
    weather: WeatherData,
    *,
    physics_mw: float,
    capacity_mw: float,
    ptf_price: float | None = None,
) -> list[float]:
    """Build inference feature vector in canonical schema order."""
    defaults = feature_defaults()
    return [
        float(physics_mw),
        float(weather.timestamp.hour),
        float(capacity_mw),
        float(ptf_price if ptf_price is not None else defaults["ptf_price"]),
    ]


def build_training_vector(
    *,
    physics_mw: float,
    hour_idx: float,
    capacity_mw: float,
    ptf_price: float,
) -> list[float]:
    """Build training feature vector using the same schema as inference."""
    return [
        float(physics_mw),
        float(hour_idx),
        float(capacity_mw),
        float(ptf_price),
    ]


def validate_feature_vector(vector: Sequence[float]) -> None:
    if len(vector) != len(HYBRID_FEATURE_NAMES):
        raise ValueError(
            f"Feature vector length mismatch: expected={len(HYBRID_FEATURE_NAMES)} got={len(vector)}"
        )


def validate_feature_names(feature_names: Sequence[str]) -> None:
    if list(feature_names) != list(HYBRID_FEATURE_NAMES):
        raise ValueError(
            f"Feature name contract mismatch: expected={list(HYBRID_FEATURE_NAMES)} got={list(feature_names)}"
        )


def assert_no_leakage_features(feature_names: Sequence[str]) -> None:
    overlap = set(feature_names) & LEAKAGE_FORBIDDEN_FIELDS
    if overlap:
        raise ValueError(f"Leakage fields cannot be model features: {sorted(overlap)}")


def parse_hour_index(timestamp: Any) -> float:
    if not timestamp:
        return 12.0
    try:
        parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        return float(parsed.hour)
    except ValueError:
        return 12.0
