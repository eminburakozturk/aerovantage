"""Tree SHAP attribution for hybrid forecast models."""

from __future__ import annotations

from typing import Any, Sequence

EXPLAINABILITY_VERSION = "1.0.0"


def compute_tree_attribution(
    booster: Any,
    feature_vector: Sequence[float],
    feature_names: Sequence[str],
) -> dict[str, Any]:
    """Compute XGBoost tree SHAP contributions via pred_contribs.

    Supports both raw ``Booster`` and sklearn ``XGBRegressor`` / ``XGBModel``.
    """
    import numpy as np
    import xgboost as xgb

    x = np.array([feature_vector], dtype=float)
    names = [str(name) for name in feature_names]
    dmat = xgb.DMatrix(x, feature_names=names)

    raw_booster = booster.get_booster() if hasattr(booster, "get_booster") else booster
    contribs = raw_booster.predict(dmat, pred_contribs=True)[0]
    bias = float(contribs[-1])
    shap_values = [float(value) for value in contribs[:-1]]
    total_abs = sum(abs(value) for value in shap_values) or 1.0

    if hasattr(booster, "get_booster"):
        prediction_mw = float(np.asarray(booster.predict(x)).reshape(-1)[0])
    else:
        prediction_mw = float(raw_booster.predict(dmat)[0])

    features = [
        {
            "feature": name,
            "shap_value": round(value, 4),
            "weight": round(abs(value) / total_abs, 4),
        }
        for name, value in zip(names, shap_values)
    ]
    features.sort(key=lambda item: item["weight"], reverse=True)

    return {
        "method": "xgboost_tree_shap",
        "bias": round(bias, 4),
        "prediction_mw": round(prediction_mw, 4),
        "features": features,
    }


def to_feature_importance(attribution: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert attribution payload to briefing-friendly feature importance rows."""
    rows: list[dict[str, Any]] = []
    for item in attribution.get("features", []):
        label = str(item.get("feature") or "unknown")
        rows.append(
            {
                "feature": _feature_label(label),
                "weight": float(item.get("weight") or 0.0),
                "shap_value": float(item.get("shap_value") or 0.0),
            }
        )
    return rows


def _feature_label(feature_name: str) -> str:
    mapping = {
        "physics_mw": "Fizik model çıktısı",
        "hour_idx": "Saatlik mevsimsellik",
        "capacity_mw": "Santral kapasitesi",
        "ptf_price": "PTF fiyat sinyali",
    }
    return mapping.get(feature_name, feature_name)
