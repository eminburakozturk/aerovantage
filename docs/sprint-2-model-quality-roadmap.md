# Sprint 2 Model Quality Notes

Bu dokuman Sprint 2 kapsaminda model kalite iyilestirmeleri icin uygulanan teknik ilkeleri kaydeder.

## Confidence Stack
- `modules/forecast/production/confidence_stack.py`:
  - `base_confidence` -> `confidence_calibrated` (drift-aware)
  - `prediction_interval` (point/lower/upper/margin)
  - `coverage` (actual'in band icinde kalma orani, target %80)
  - Endpoint: `GET /monitoring/confidence-stack`

## Drift Baseline
- Baseline penceresi: son 7 metric kaydi (`modules/monitoring/drift.py`).
- Yeterli orneklemde (`>=3`) z-score tabanli drift: `|z| >= 2.0`.
- Dusuk orneklemde legacy esik fallback:
  - `mape_drift`: `residual_mape >= 3.0`
  - `cost_drift`: `residual_cost >= 20000`
- Drift metadata: `residual_mape`, `residual_cost`, `mape_z_score`, `cost_z_score`, `drift_severity`.
- Ozet endpoint: `GET /monitoring/drift-summary`

## Evaluation Registry
- Pipeline her calistiginda `pipeline_metrics.jsonl` kaydina asagidaki alanlar yazilir:
  - `asset_id`, `target_date`, `mape_percentage`, `risk_score`, `total_imbalance_cost_tl`
  - `drift`, `confidence_calibrated`, `rules_count`

## Validation Framework
- `modules/forecast/production/validation.py`:
  - Chronological time-series holdout (`split_time_series_chronological`)
  - Acceptance gate: `max_val_mae`, `max_train_val_mae_gap`, `min_val_samples`
  - Retrain promotion: yeni artifact yalnizca `val_mae` incumbent'tan iyi/esit ise deploy edilir
  - Hybrid model metadata: `validation.deployable`

## Recommendation Quality Proxy
- `recommendation_quality` metrikleri (`modules/recommendation/quality.py`):
  - `action_coverage`: aksiyon verilen run orani
  - `improved_after_action_ratio`: aksiyon sonrasi risk azalimi orani
  - `cost_improved_after_action_ratio`: aksiyon sonrasi maliyet azalimi orani
  - `mape_improved_after_action_ratio`: aksiyon sonrasi MAPE azalimi orani
  - `quality_score`: agirlikli bilesik skor (0-100)
  - `samples`, `evaluated_actions`, `reportable`
  - Haftalik rapor: `GET /monitoring/recommendation-quality`

## Alert Quality Proxy
- `modules/alerting/quality.py`:
  - `precision_proxy`: metriklerle desteklenen alarm orani
  - `false_positive_rate`: desteksiz ve sonraki run'da iyilesen alarm orani
  - `outcome_confirmed_rate`: sonraki run'da riskin yuksek kaldigi alarm orani
  - Haftalik rapor: `GET /monitoring/alert-quality`

## Explainability
- `modules/forecast/production/explainability.py`:
  - XGBoost tree SHAP (`pred_contribs`) ile feature attribution
  - Endpoint: `GET /monitoring/model-attribution`

## Decision Causality
- `modules/recommendation/causality.py`:
  - Action vs control cohort `causality_lift`
  - Endpoint: `GET /monitoring/decision-causality`

## Production Hardening
- `modules/ml_registry/registry.py`:
  - Model lineage: feature schema, dataset runs, hyperparameters, git commit
  - Registry index: `data/models/registry.jsonl`
  - Experiment bundle: `experiment.json`, `metrics.json`, `model.json`
  - Endpoints: `/monitoring/model-registry`, `/monitoring/experiments/{id}`

