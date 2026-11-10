"""Model registry — traceable model lineage for production hardening."""

from __future__ import annotations

import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core.config import get_settings

MODEL_REGISTRY_VERSION = "1.0.0"
_REGISTRY_FILE = "registry.jsonl"


def _registry_path() -> Path:
    root = get_settings().project_root / "data" / "models"
    root.mkdir(parents=True, exist_ok=True)
    return root / _REGISTRY_FILE


def _experiments_root() -> Path:
    root = get_settings().project_root / "data" / "models" / "experiments"
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_git_commit() -> str:
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return output.strip() or "unknown"
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def register_model_run(
    *,
    asset_id: str,
    model_info: dict[str, Any],
    meta: dict[str, Any],
    dataset_runs: int,
    hyperparameters: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Register a promoted model and persist experiment tracking bundle."""
    experiment_id = f"exp-{asset_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    created_at = datetime.now(timezone.utc).isoformat()
    git_commit = resolve_git_commit()

    validation = meta.get("validation") or model_info.get("validation") or {}
    entry = {
        "registry_version": MODEL_REGISTRY_VERSION,
        "experiment_id": experiment_id,
        "asset_id": asset_id,
        "model_type": model_info.get("type", "unknown"),
        "feature_schema_version": model_info.get("feature_schema_version"),
        "feature_names": model_info.get("feature_names", []),
        "trained_samples": model_info.get("trained_samples", 0),
        "dataset_source": "pipeline_history",
        "dataset_runs": dataset_runs,
        "hyperparameters": hyperparameters or _default_hyperparameters(),
        "git_commit": git_commit,
        "artifact_path": model_info.get("artifact_path"),
        "train_mae": meta.get("train_mae"),
        "val_mae": meta.get("val_mae"),
        "deployable": validation.get("deployable"),
        "created_at": created_at,
    }

    _append_registry_entry(entry)
    _write_experiment_bundle(experiment_id, entry, meta, model_info)
    return entry


def _default_hyperparameters() -> dict[str, Any]:
    return {
        "n_estimators": 80,
        "max_depth": 4,
        "learning_rate": 0.08,
        "subsample": 0.85,
        "colsample_bytree": 0.85,
    }


def _append_registry_entry(entry: dict[str, Any]) -> None:
    path = _registry_path()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _write_experiment_bundle(
    experiment_id: str,
    entry: dict[str, Any],
    meta: dict[str, Any],
    model_info: dict[str, Any],
) -> Path:
    bundle_dir = _experiments_root() / experiment_id
    bundle_dir.mkdir(parents=True, exist_ok=True)

    experiment_doc = {
        "experiment_id": experiment_id,
        "asset_id": entry["asset_id"],
        "model_type": entry["model_type"],
        "feature_schema_version": entry["feature_schema_version"],
        "feature_names": entry["feature_names"],
        "dataset_source": entry["dataset_source"],
        "dataset_runs": entry["dataset_runs"],
        "hyperparameters": entry["hyperparameters"],
        "git_commit": entry["git_commit"],
        "created_at": entry["created_at"],
    }
    metrics_doc = {
        "experiment_id": experiment_id,
        "trained_samples": entry["trained_samples"],
        "train_mae": entry["train_mae"],
        "val_mae": entry["val_mae"],
        "validation": meta.get("validation") or model_info.get("validation") or {},
    }
    model_doc = {
        "experiment_id": experiment_id,
        "artifact_path": entry["artifact_path"],
        "model_type": entry["model_type"],
        "feature_schema_version": entry["feature_schema_version"],
        "feature_names": entry["feature_names"],
        "deployable": entry["deployable"],
    }

    (bundle_dir / "experiment.json").write_text(
        json.dumps(experiment_doc, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (bundle_dir / "metrics.json").write_text(
        json.dumps(metrics_doc, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (bundle_dir / "model.json").write_text(
        json.dumps(model_doc, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return bundle_dir


def list_registry_entries(
    *,
    asset_id: Optional[str] = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    path = _registry_path()
    if not path.exists():
        return []

    entries: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if asset_id and entry.get("asset_id") != asset_id:
                continue
            entries.append(entry)
    return list(reversed(entries[-limit:]))


def get_latest_registry_entry(asset_id: str) -> Optional[dict[str, Any]]:
    entries = list_registry_entries(asset_id=asset_id, limit=1)
    return entries[0] if entries else None


def load_experiment_bundle(experiment_id: str) -> Optional[dict[str, Any]]:
    bundle_dir = _experiments_root() / experiment_id
    if not bundle_dir.exists():
        return None

    payload: dict[str, Any] = {"experiment_id": experiment_id}
    for name in ("experiment", "metrics", "model"):
        file_path = bundle_dir / f"{name}.json"
        if file_path.exists():
            payload[name] = json.loads(file_path.read_text(encoding="utf-8"))
    return payload
