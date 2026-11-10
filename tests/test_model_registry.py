"""Model registry and experiment tracking tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from modules.ml_registry.registry import (
    MODEL_REGISTRY_VERSION,
    get_latest_registry_entry,
    list_registry_entries,
    load_experiment_bundle,
    register_model_run,
)


@pytest.fixture()
def registry_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    models_dir = tmp_path / "data" / "models"
    models_dir.mkdir(parents=True)

    class _Settings:
        project_root = tmp_path

    monkeypatch.setattr("modules.ml_registry.registry.get_settings", lambda: _Settings())
    return models_dir


def test_register_model_run_writes_registry_and_bundle(registry_dir: Path) -> None:
    entry = register_model_run(
        asset_id="RES-BAL-01",
        model_info={
            "type": "hybrid_xgb",
            "feature_schema_version": "1.0.0",
            "feature_names": ["physics_mw", "hour_idx", "capacity_mw", "ptf_price"],
            "trained_samples": 48,
            "artifact_path": str(registry_dir / "hybrid_xgb_RES-BAL-01.json"),
            "validation": {"deployable": True},
        },
        meta={
            "train_mae": 1.2,
            "val_mae": 1.8,
            "validation": {"deployable": True},
        },
        dataset_runs=12,
    )

    assert entry["experiment_id"].startswith("exp-RES-BAL-01-")
    assert entry["registry_version"] == MODEL_REGISTRY_VERSION
    assert entry["git_commit"]

    registry_file = registry_dir / "registry.jsonl"
    assert registry_file.exists()

    bundle = load_experiment_bundle(entry["experiment_id"])
    assert bundle is not None
    assert bundle["experiment"]["asset_id"] == "RES-BAL-01"
    assert bundle["metrics"]["val_mae"] == 1.8
    assert bundle["model"]["feature_names"]

    experiment_path = registry_dir / "experiments" / entry["experiment_id"]
    assert (experiment_path / "experiment.json").exists()
    assert (experiment_path / "metrics.json").exists()
    assert (experiment_path / "model.json").exists()


def test_list_and_get_latest_registry_entry(registry_dir: Path) -> None:
    register_model_run(
        asset_id="RES-BAL-01",
        model_info={"type": "hybrid_xgb", "feature_names": [], "trained_samples": 10},
        meta={"train_mae": 1.0, "val_mae": 1.1},
        dataset_runs=3,
    )
    entries = list_registry_entries(asset_id="RES-BAL-01", limit=5)
    latest = get_latest_registry_entry("RES-BAL-01")

    assert len(entries) == 1
    assert latest is not None
    assert latest["asset_id"] == "RES-BAL-01"


def test_monitoring_model_registry_endpoint(auth_headers: dict[str, str]) -> None:
    client = TestClient(app)
    response = client.get("/api/v1/monitoring/model-registry?limit=10", headers=auth_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["version"] == MODEL_REGISTRY_VERSION
    assert "entries" in data
