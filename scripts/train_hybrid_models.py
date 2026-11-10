#!/usr/bin/env python3
"""Hybrid XGBoost modellerini tüm varlıklar için yeniden eğitir."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from core.logger import get_logger
from modules.asset_registry.service import AssetRegistryService
from modules.forecast.production.models.xgb_hybrid_model import HybridWindPowerModel


def main() -> int:
    logger = get_logger("scripts.train_hybrid_models")
    assets = AssetRegistryService().get_all_assets()
    summaries: list[dict[str, object]] = []
    logger.info("Hybrid model eğitim işi başladı: assets=%s", len(assets))

    for asset in assets:
        model = HybridWindPowerModel(capacity_mw=asset.capacity_mw, asset_id=asset.id)
        model.retrain_from_history()
        info = model.model_info
        validation = info.get("validation") or {}
        registry = info.get("registry") or {}
        summaries.append(
            {
                "asset_id": asset.id,
                "model_type": info.get("type"),
                "trained_samples": info.get("trained_samples"),
                "artifact_path": info.get("artifact_path"),
                "deployable": validation.get("deployable"),
                "acceptance_passed": (validation.get("acceptance_gate") or {}).get("passed"),
                "promotion_reason": (validation.get("promotion") or {}).get("reason"),
                "experiment_id": registry.get("experiment_id"),
                "git_commit": registry.get("git_commit"),
            }
        )
        logger.info(
            "Asset eğitim tamamlandı: asset_id=%s type=%s samples=%s",
            asset.id,
            info.get("type"),
            info.get("trained_samples"),
        )

    output_dir = Path(__file__).resolve().parent.parent / "data" / "models"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "training_report.json"
    report_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.utcnow().isoformat(),
                "asset_count": len(assets),
                "results": summaries,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    logger.info("Eğitim raporu kaydedildi: %s", report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

