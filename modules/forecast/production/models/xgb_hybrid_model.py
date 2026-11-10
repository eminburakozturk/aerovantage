"""XGBoost + fizik tabanli hibrit ruzgar gucu modeli."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from core.config import get_settings
from core.logger import get_logger
from core.storage import PipelineStorage
from modules.ml_registry.registry import register_model_run
from modules.data_hub.schemas import WeatherData
from modules.forecast.production.explainability import EXPLAINABILITY_VERSION, compute_tree_attribution
from modules.forecast.production.feature_schema import (
    FEATURE_SCHEMA_VERSION,
    HYBRID_FEATURE_NAMES,
    build_inference_vector,
    build_training_vector,
    parse_hour_index,
    validate_feature_names,
)
from modules.forecast.production.models.wind_model import WindPowerModel
from modules.forecast.production.validation import (
    DEFAULT_ACCEPTANCE_CRITERIA,
    build_validation_report,
    regression_metrics,
    split_time_series_chronological,
    walk_forward_time_series_validation,
)

_MIN_TRAINING_SAMPLES = 24
_DEFAULT_MODEL_ARTIFACT_DIR = Path("data") / "models"


class HybridWindPowerModel:
    """Power-curve fizik modeli + XGBoost residual duzeltmesi.

    Yeterli gecmis pipeline verisi yoksa saf fizik modeline doner.
    """

    def __init__(
        self,
        capacity_mw: float = 50.0,
        physics_model: Optional[WindPowerModel] = None,
        storage: Optional[PipelineStorage] = None,
        asset_id: Optional[str] = None,
    ) -> None:
        self.capacity_mw = capacity_mw
        self._physics = physics_model or WindPowerModel(capacity_mw=capacity_mw)
        self._storage = storage or PipelineStorage()
        self._asset_id = asset_id
        self._logger = get_logger("forecast.hybrid_xgb")
        self._booster: Any = None
        self._trained_samples = 0
        self._validation_report: dict[str, Any] = {}
        self._registry_entry: dict[str, Any] = {}
        self._settings = get_settings()
        self._model_dir = (self._settings.project_root / _DEFAULT_MODEL_ARTIFACT_DIR).resolve()
        self._model_dir.mkdir(parents=True, exist_ok=True)
        self._artifact_path = self._model_dir / f"hybrid_xgb_{self._asset_id or 'default'}.json"
        self._meta_path = self._model_dir / f"hybrid_xgb_{self._asset_id or 'default'}.meta.json"
        self._load_existing_model()
        if self._booster is None:
            self._try_train()

    def _load_existing_model(self) -> None:
        if not self._artifact_path.exists():
            return
        try:
            from xgboost import XGBRegressor

            model = XGBRegressor()
            model.load_model(self._artifact_path.as_posix())
            self._booster = model
            if self._meta_path.exists():
                metadata = json.loads(self._meta_path.read_text(encoding="utf-8"))
                validate_feature_names(metadata.get("feature_names", []))
                self._trained_samples = int(metadata.get("trained_samples", 0))
                self._validation_report = metadata.get("validation", {})
                if self._validation_report.get("deployable") is False:
                    self._logger.warning(
                        "Deployable olmayan artifact reddedildi: asset_id=%s",
                        self._asset_id,
                    )
                    self._booster = None
                    return
            self._logger.info(
                "XGBoost artifact yüklendi: asset_id=%s path=%s samples=%s",
                self._asset_id,
                self._artifact_path,
                self._trained_samples,
            )
        except Exception as exc:
            self._logger.warning("XGBoost artifact yüklenemedi: %s", exc)
            self._booster = None

    def _read_incumbent_meta(self) -> dict[str, Any]:
        if not self._meta_path.exists():
            return {}
        try:
            return json.loads(self._meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _try_train(self) -> None:
        if not self._asset_id:
            return

        incumbent_meta = self._read_incumbent_meta()
        incumbent_val_mae = incumbent_meta.get("val_mae")
        if incumbent_val_mae is not None:
            incumbent_val_mae = float(incumbent_val_mae)

        samples: list[tuple[str, list[float], float]] = []
        for run in self._storage.get_recent_runs(limit=120):
            if run.get("asset_id") != self._asset_id:
                continue
            capacity = float(run.get("capacity_mw", self.capacity_mw))
            run_key = str(run.get("target_date") or run.get("saved_at") or "")
            for hour in run.get("hours") or []:
                actual = hour.get("actual_mw")
                forecast = hour.get("forecast_mw")
                if actual is None or forecast is None:
                    continue
                hour_key = str(hour.get("timestamp") or "")
                sort_key = f"{run_key}:{hour_key}"
                hour_idx = parse_hour_index(hour.get("timestamp"))
                physics_mw = max(0.0, float(forecast))
                ptf_price = float(hour.get("ptf_price") or 0.0)
                samples.append(
                    (
                        sort_key,
                        build_training_vector(
                            physics_mw=physics_mw,
                            hour_idx=hour_idx,
                            capacity_mw=capacity,
                            ptf_price=ptf_price,
                        ),
                        float(actual),
                    )
                )

        samples.sort(key=lambda item: item[0])
        features = [item[1] for item in samples]
        targets = [item[2] for item in samples]

        if len(features) < _MIN_TRAINING_SAMPLES:
            self._logger.info(
                "XGBoost egitimi atlandi: asset_id=%s samples=%s",
                self._asset_id,
                len(features),
            )
            return

        try:
            from xgboost import XGBRegressor

            split = split_time_series_chronological(
                features,
                targets,
                min_val_samples=DEFAULT_ACCEPTANCE_CRITERIA.min_val_samples,
            )
            x_train, y_train = split.x_train, split.y_train
            x_val, y_val = split.x_val, split.y_val

            model = XGBRegressor(
                n_estimators=80,
                max_depth=4,
                learning_rate=0.08,
                subsample=0.85,
                colsample_bytree=0.85,
                reg_alpha=0.1,
                reg_lambda=1.0,
                objective="reg:squarederror",
                random_state=42,
            )
            model.fit(x_train, y_train)
            train_pred = model.predict(x_train)
            val_pred = model.predict(x_val)
            train_metrics = regression_metrics(y_train, train_pred)
            val_metrics = regression_metrics(y_val, val_pred)
            walk_forward = walk_forward_time_series_validation(
                features,
                targets,
                max_mean_val_mae=DEFAULT_ACCEPTANCE_CRITERIA.max_val_mae,
            )
            validation_report = build_validation_report(
                train_metrics=train_metrics,
                val_metrics=val_metrics,
                val_samples=split.val_size,
                incumbent_val_mae=incumbent_val_mae,
                walk_forward=walk_forward,
            )
            self._validation_report = validation_report

            if not validation_report["deployable"]:
                self._logger.info(
                    "XGBoost artifact promote edilmedi: asset_id=%s acceptance=%s promotion=%s",
                    self._asset_id,
                    validation_report["acceptance_gate"]["passed"],
                    validation_report["promotion"]["promoted"],
                )
                if incumbent_meta:
                    self._load_existing_model()
                return

            self._booster = model
            self._trained_samples = len(features)
            model.save_model(self._artifact_path.as_posix())
            self._meta_path.write_text(
                json.dumps(
                    {
                        "asset_id": self._asset_id,
                        "trained_samples": self._trained_samples,
                        "feature_schema_version": FEATURE_SCHEMA_VERSION,
                        "feature_names": list(HYBRID_FEATURE_NAMES),
                        "train_mae": train_metrics["mae"],
                        "val_mae": val_metrics["mae"],
                        "validation": validation_report,
                        "saved_at": datetime.utcnow().isoformat(),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            meta = json.loads(self._meta_path.read_text(encoding="utf-8"))
            dataset_runs = len(
                {
                    run.get("target_date")
                    for run in self._storage.get_recent_runs(limit=120)
                    if run.get("asset_id") == self._asset_id
                }
            )
            self._registry_entry = register_model_run(
                asset_id=self._asset_id,
                model_info=self.model_info,
                meta=meta,
                dataset_runs=dataset_runs,
            )
            self._logger.info(
                "XGBoost hibrit model egitildi: asset_id=%s samples=%s train_mae=%.4f val_mae=%.4f",
                self._asset_id,
                len(features),
                train_metrics["mae"],
                val_metrics["mae"],
            )
        except Exception as exc:
            self._logger.warning("XGBoost egitimi basarisiz, fizik modeli kullanilacak: %s", exc)
            self._booster = None

    def retrain_from_history(self) -> None:
        """Artifact olsa bile geçmiş veriden modeli yeniden eğitir."""
        self._try_train()

    def predict(self, weather: WeatherData) -> float:
        """Saatlik MW tahmini — fizik + opsiyonel ML residual."""
        physics_mw = self._physics.predict(weather)

        if self._booster is None:
            return physics_mw

        try:
            import numpy as np

            feature_vector = build_inference_vector(
                weather,
                physics_mw=physics_mw,
                capacity_mw=self.capacity_mw,
            )
            x = np.array([feature_vector], dtype=float)
            ml_mw = float(self._booster.predict(x)[0])
            blended = 0.35 * physics_mw + 0.65 * ml_mw
            return round(max(0.0, min(self.capacity_mw, blended)), 4)
        except Exception as exc:
            self._logger.warning("XGBoost tahmin hatasi, fizik modeli: %s", exc)
            return physics_mw

    def explain(self, weather: WeatherData) -> dict[str, Any]:
        """Return SHAP-style attribution for a single inference point."""
        physics_mw = self._physics.predict(weather)
        if self._booster is None:
            return {
                "version": EXPLAINABILITY_VERSION,
                "method": "physics_only",
                "prediction_mw": round(physics_mw, 4),
                "physics_mw": round(physics_mw, 4),
                "features": [
                    {
                        "feature": "physics_mw",
                        "shap_value": round(physics_mw, 4),
                        "weight": 1.0,
                    }
                ],
            }

        feature_vector = build_inference_vector(
            weather,
            physics_mw=physics_mw,
            capacity_mw=self.capacity_mw,
        )
        try:
            attribution = compute_tree_attribution(
                self._booster,
                feature_vector,
                HYBRID_FEATURE_NAMES,
            )
        except Exception as exc:
            self._logger.warning("SHAP attribution başarısız, fizik attribution: %s", exc)
            return {
                "version": EXPLAINABILITY_VERSION,
                "method": "physics_fallback",
                "prediction_mw": round(physics_mw, 4),
                "physics_mw": round(physics_mw, 4),
                "features": [
                    {
                        "feature": "physics_mw",
                        "shap_value": round(physics_mw, 4),
                        "weight": 1.0,
                    }
                ],
                "error": str(exc),
            }
        return {
            "version": EXPLAINABILITY_VERSION,
            **attribution,
            "physics_mw": round(physics_mw, 4),
            "blend_weights": {"physics": 0.35, "ml": 0.65},
        }

    @property
    def model_info(self) -> dict[str, Any]:
        return {
            "type": "hybrid_xgb" if self._booster else "physics_only",
            "trained_samples": self._trained_samples,
            "capacity_mw": self.capacity_mw,
            "artifact_path": self._artifact_path.as_posix(),
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "feature_names": list(HYBRID_FEATURE_NAMES),
            "validation": self._validation_report,
            "registry": self._registry_entry,
        }
