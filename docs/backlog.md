# Engineering Backlog

> **KİLİTLİ:** Tüm geliştirme `docs/AEROVANTAGE-FINAL-ROADMAP.md` dosyasına göre yapılır.  
> Feature Freeze + UI Freeze aktif. Yeni roadmap üretilmez.  
> **v1.x:** Feature Complete — bakım politikası [`V1-MAINTENANCE-POLICY.md`](V1-MAINTENANCE-POLICY.md). Yeni fikirler → [`V2-BACKLOG.md`](V2-BACKLOG.md) (v1.x’te uygulanmaz).

## Production Hardening (Ayrı Sprint — Roadmap Dışı)
- [x] `NEXT_PUBLIC_API_SECRET_KEY` mimarisini kaldır: frontend bearer secret taşımayacak, server-side authentication modeline geçilecek.
  - Implemented: `frontend/src/app/api/backend/[...path]/route.ts` BFF proxy + `API_SECRET_KEY` (server-only).

## Sprint 3 — Operational Intelligence Reliability (Discovery Locked)

### Scope Split
- **Sprint 3A — Data Reliability:** EPİAŞ, SCADA, fallback telemetry, data quality gates
- **Sprint 3B — Model Reliability:** feature schema parity, leakage guard, validation, drift
- **Sprint 3C — Decision Reliability:** recommendation quality, confidence + interval + coverage

### P1 (Sprint 3 Core)
- [x] **P1-01 — Data Contract Audit + Versioned Contracts**
  - Forecast, Risk, AI, Monitoring katmanları arasında tek kaynak input/validation/output sözleşmeleri oluşturulacak.
  - Örnek akış: `WeatherData -> ForecastInput -> Prediction -> RiskInput -> RecommendationInput`.
  - Contract'lar versioned olacak (breaking değişiklik kuralları ile).
  - Implemented: `core/data_contracts.py`, `core/pipeline.py`, `docs/data-contracts-v1.md`, `tests/test_data_contracts.py`.
- [x] **P1-02 — EPİAŞ Live Response Mapping Production Tamamlama**
  - Başarılı live response sonrası mock fallback davranışı kaldırılacak.
  - Mapping eksikliği için explicit degraded sinyal üretilecek.
- [x] **P1-03 — SCADA Production Adapter Standardization (Influx/REST)**
  - Influx/REST adapter path'leri production-ready hale getirilecek.
  - Mock/real ayrımı pipeline ve monitoring katmanına taşınacak.
  - Implemented: `modules/data_hub/scada.py`, `modules/performance/service.py`, `core/pipeline.py`, `tests/test_scada.py`.
- [x] **P1-04 — Fallback Telemetry + Degraded State Visibility**
  - Source/reason bazlı fallback oranı ve degraded run metrikleri izlenebilir olacak.
  - Monitoring çıktıları operasyonel karar için yeterli sinyal sağlayacak.
  - Implemented: `core/pipeline.py`, `api/routes/monitoring.py`, `frontend/src/lib/api/types.ts`, `frontend/src/lib/api/endpoints.ts`, `tests/test_pipeline_architecture.py`.
- [x] **P1-05 — Data Quality Gates in CI (Mandatory)**
  - Completeness/timeliness/consistency kontrolleri CI'da fail-fast zorunlu kapı olacak.
  - Implemented: `.github/workflows/quality-gates.yml` (backend data quality tests + frontend lint/typecheck/build mandatory gates).
- [x] **P1-06 — Feature Schema Single Source (Feature Parity)**
  - `modules/forecast/production/feature_schema.py` tek kaynak olarak eklendi.
  - Hybrid XGB train/serve vektörleri aynı şemadan üretiliyor; `imbalance_cost_tl` feature set'ten çıkarıldı.
  - `tests/test_feature_schema.py` ile parity ve leakage guard doğrulanıyor.
- [x] **P1-07 — Recommendation Engine Quality (End-of-Sprint P1)**
  - `modules/recommendation/quality.py` tek kaynak olarak eklendi.
  - Proxy metrikler: `action_coverage`, `improved_after_action_ratio`, `cost/mape_improved_after_action_ratio`, `quality_score`.
  - `GET /monitoring/recommendation-quality` haftalık rapor endpoint'i eklendi.
  - Pipeline metrics ve AI brifing bu modüle bağlandı; `tests/test_recommendation_quality.py` ile doğrulanıyor.

### P2 (Post-Core Reliability)
- [x] **P2-01 — Validation Framework Hardening**
  - `modules/forecast/production/validation.py`: chronological time-series split, acceptance gate, retrain promotion.
  - Hybrid model artifact yalnızca `deployable` adaylarda promote ediliyor; aksi halde incumbent korunuyor.
  - `tests/test_model_validation.py` ve training report alanları güncellendi.
- [x] **P2-02 — Drift Detection Statistical Upgrade**
  - `modules/monitoring/drift.py`: z-score tabanlı drift + residual izleme, küçük örneklemlerde legacy fallback.
  - Pipeline drift metadata genişletildi (`mape_z_score`, `residual_*`, `drift_severity`).
  - `GET /monitoring/drift-summary` endpoint'i ve `tests/test_drift_detection.py` eklendi.
- [x] **P2-03 — Alert Quality Evaluation**
  - `modules/alerting/quality.py`: precision proxy, false-positive rate, outcome-confirmed rate.
  - `GET /monitoring/alert-quality` haftalık rapor endpoint'i eklendi.
  - Pipeline metadata/metrics ve `tests/test_alert_quality.py` ile doğrulanıyor.
- [x] **P2-04 — Confidence Stack Maturity**
  - `modules/forecast/production/confidence_stack.py`: Prediction → Confidence → Interval → Coverage zinciri.
  - Pipeline metadata/metrics ve `GET /monitoring/confidence-stack` endpoint'i eklendi.
  - `tests/test_confidence_stack.py` ile doğrulanıyor.

### P3 (Deferred / Strategic)
- [x] **P3-01 — Explainability Deepening (SHAP/Attribution)**
  - `modules/forecast/production/explainability.py`: XGBoost `pred_contribs` tree SHAP attribution.
  - Hybrid model `explain()`, pipeline `model_attribution`, briefing ve `GET /monitoring/model-attribution`.
- [x] **P3-02 — Decision Causality Loop**
  - `modules/recommendation/causality.py`: action vs control cohort causality lift.
  - Pipeline `decision_causality` metadata ve `GET /monitoring/decision-causality` endpoint'i.

### Production Hardening Backlog (Tracked, Not Sprint 3 Implementation)
- [x] **PH-01 — Model Registry (Mandatory before Production Hardening)**
  - `modules/ml_registry/registry.py`: dataset/feature/parametre/commit lineage + `registry.jsonl`.
  - Hybrid model promote sonrası otomatik kayıt; `GET /monitoring/model-registry`.
- [x] **PH-02 — Experiment Tracking (Mandatory before Production Hardening)**
  - Her kayıt için `data/models/experiments/{id}/experiment.json`, `metrics.json`, `model.json`.
  - `GET /monitoring/experiments/{experiment_id}` ve `/experiments/latest/{asset_id}`.

### Acceptance Criteria
- Katmanlar arası veri sözleşmeleri tek kaynakta tanımlı, versioned ve kırıcı değişiklik kuralları net.
- EPİAŞ ve SCADA için live path başarı oranı ölçülür, fallback nedenleri görünür.
- Fallback/degraded state, monitoring çıktısında açık ve sorgulanabilir.
- Data quality gate'leri CI'da zorunlu; ihlal durumunda pipeline promotion engellenir.
- Feature schema train/serve parity testleri sürekli geçer.
- Recommendation quality metrikleri haftalık raporlanabilir durumda olur.

### Risk
- Live connector eksikliği nedeniyle mock fallback'in sessizce kaliteyi maskelemesi.
- Feature mismatch/leakage nedeniyle model performansının yanlış ölçülmesi.
- Data contract eksikliği nedeniyle katmanlar arası kırılma ve regresyon riski.
- Recommendation kalitesinin ölçülememesi nedeniyle operasyonel karar güveninin düşmesi.
- Sprint kapsamının aşırı büyümesi nedeniyle teslimatların dağılması.

### Dependencies
- EPİAŞ/SCADA erişim bilgileri ve canlı endpoint erişilebilirliği.
- CI pipeline üzerinde quality gate entegrasyon yetkisi.
- Monitoring/telemetry için ortak metrik şeması kararı.
- Forecast/Risk/AI katman sahipliği için sözleşme onay akışı.
- Sprint 3 sırasında kapsam disiplini: Model Registry/Experiment Tracking sadece backlog takibi.

### Done Criteria
- Sprint 3A/3B/3C kapsamındaki P1 maddeleri backlog'da tamamlandı olarak işaretlenmiş olur.
- Her P1 maddesi için ölçülebilir metrik ve doğrulama çıktısı rapora eklenir.
- Data Contract + Feature Schema tek kaynak dokümantasyonu repository'de yer alır.
- Degraded/fallback görünürlüğü operasyonel panel ve/veya monitoring endpoint'te doğrulanır.
- Sprint sonunda implementasyon dışı stratejik işler (Model Registry, Experiment Tracking) Production Hardening backlog'unda takip edilir.

## Sprint 1A Follow-up
- [x] Public API surface contract koruması eklendi (`frontend/src/lib/api.ts`):
  - `npm run check:api-contract` ile export sözleşmesi snapshot doğrulaması.
  - `scripts/api-contract.snapshot.json` ile entrypoint + barrel export contract sabitlendi.
- [x] Navigation/workspace config tek kaynak yaklaşımı güçlendirildi:
  - workspace route/meta/default-tab üretimi `workspace-config` merkezli hale getirildi.
  - layout route sabitleri `frontend/src/lib/routes.ts` altında merkezileştirildi.
  - workspace id literal tekrarları `WORKSPACE_IDS` ile azaltıldı.
- [x] Workspace route literal temizliği tamamlandı:
  - dashboard/topbar/redirect/panel linkleri merkezi route/workspace map'e alındı.
  - workspace link hardcode'ları komponent katmanından kaldırıldı.
- [x] Hata mesajı standardizasyonu:
  - `getErrorMessage()` helper ile API/UI hata dönüştürmesi tek noktaya taşındı.
  - workspace/ops/settings/reporting akışlarında duplicate catch kalıpları sadeleştirildi.
- [x] Workspace tab çözümleme standardizasyonu:
  - `resolveWorkspaceTab()` helper eklendi.
  - `workspace-shell` ve `settings` valid tab çözümlemesi tek kurala bağlandı.
- [x] Risk ve format helper standardizasyonu:
  - `operationalStatusFromRisk()` ile risk->durum eşikleri merkezileştirildi.
  - `format` katmanına tarih/saat/TL yardımcıları eklendi ve kritik ekranlarda tekrarlar azaltıldı.
- [x] Saat formatı tekrarlarının temizliği:
  - timeline/forecast/market/risk workspace tarafında `formatTimeShort()` kullanımına geçildi.
  - risk ekranında risk->renk dönüşümleri `status-level` yardımcıları ile hizalandı.
- [x] Monitoring/Assets shared helper hizalaması:
  - monitoring fetch hataları `getErrorMessage()` ile standardize edildi.
  - assets health risk görselleştirmesi `operationalStatusFromRisk()` ve `STATUS_COLORS` ile merkezileştirildi.
  - market feed maliyet biçimlendirmesi `formatCurrencyTl()` ile tekilleştirildi.
