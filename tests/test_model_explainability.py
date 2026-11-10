"""Model explainability tests."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import numpy as np
from fastapi.testclient import TestClient

from api.main import app
from modules.data_hub.schemas import WeatherData
from modules.forecast.production.explainability import (
    EXPLAINABILITY_VERSION,
    compute_tree_attribution,
    to_feature_importance,
)
from modules.forecast.production.feature_schema import HYBRID_FEATURE_NAMES
from modules.forecast.production.models.xgb_hybrid_model import HybridWindPowerModel


def _weather() -> WeatherData:
    return WeatherData(
        timestamp=datetime(2026, 7, 7, 12, 0, tzinfo=timezone.utc),
        wind_speed=8.0,
        wind_direction=180.0,
        temperature=20.0,
        air_pressure=1013.0,
    )


def test_compute_tree_attribution_uses_pred_contribs() -> None:
    raw = MagicMock()
    raw.predict.return_value = np.array([[1.5, 0.5, -0.2, 0.1, 10.0]])
    booster = MagicMock(spec=["get_booster", "predict"])
    booster.get_booster.return_value = raw
    booster.predict.return_value = np.array([12.0])

    result = compute_tree_attribution(booster, [10.0, 12.0, 50.0, 1800.0], HYBRID_FEATURE_NAMES)

    assert result["method"] == "xgboost_tree_shap"
    assert result["prediction_mw"] == 12.0
    assert len(result["features"]) == 4
    assert sum(item["weight"] for item in result["features"]) == 1.0
    assert raw.predict.call_args.kwargs.get("pred_contribs") is True


def test_to_feature_importance_maps_labels() -> None:
    rows = to_feature_importance(
        {
            "features": [
                {"feature": "physics_mw", "shap_value": 1.2, "weight": 0.6},
                {"feature": "hour_idx", "shap_value": 0.3, "weight": 0.4},
            ]
        }
    )
    assert rows[0]["feature"] == "Fizik model çıktısı"


def test_hybrid_model_explain_physics_only_without_booster() -> None:
    model = HybridWindPowerModel(capacity_mw=30.0)
    model._booster = None
    explanation = model.explain(_weather())

    assert explanation["version"] == EXPLAINABILITY_VERSION
    assert explanation["method"] == "physics_only"
    assert explanation["features"][0]["feature"] == "physics_mw"


def test_monitoring_model_attribution_endpoint(auth_headers: dict[str, str]) -> None:
    client = TestClient(app)
    trigger = client.post(
        "/api/v1/pipeline/trigger-pipeline",
        json={"asset_id": "RES-BAL-01", "target_date": "2026-07-06"},
        headers=auth_headers,
    )
    assert trigger.status_code == 200, trigger.text
    assert "model_attribution" in trigger.json()["metadata"]

    response = client.get(
        "/api/v1/monitoring/model-attribution?asset_id=RES-BAL-01",
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["found"] is True
    assert "features" in data
