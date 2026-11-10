# Data Contracts v1.0.0

Sprint 3 P1-01 kapsamında Forecast, Risk, AI ve Monitoring katmanları arasindaki veri sozlesmeleri tek kaynakta tanimlanmistir.

## Contract Boundaries

- `forecast_to_performance`
  - Source: `forecast`
  - Target: `performance`
  - Output schema: `PredictionContract`

- `performance_to_risk`
  - Source: `performance`
  - Target: `risk`
  - Output schema: `RiskInputContract`

- `risk_to_ai`
  - Source: `risk`
  - Target: `ai`
  - Output schema: `RecommendationInputContract`

- `pipeline_to_monitoring`
  - Source: `pipeline`
  - Target: `monitoring`
  - Output schema: `MonitoringContract`

## Versioning Rule

- Active version: `1.0.0`
- Breaking degisiklikler major version artisi gerektirir.
- Non-breaking field addition degisiklikleri minor version artisi gerektirir.
- Patch duzeyindeki degisiklikler validasyon davranisini degistirmeden dokumantasyon ve dahili iyilestirmeler icin kullanilir.

## Single Source of Truth

- Contract tanimlari ve runtime validasyonlari: `core/data_contracts.py`
- Pipeline adimlarinda contract enforcement: `core/pipeline.py`
- Contract regression testleri: `tests/test_data_contracts.py`
