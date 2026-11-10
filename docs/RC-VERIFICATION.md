# AeroVantage — Release Candidate Verification

> **FAZ 6** — Mevcut capability'lerin uçtan uca doğrulama matrisi.  
> Bu dokümanda **yeni kod yok**; yalnızca mevcut davranış, testler ve monitoring görünürlüğü kayıt altına alınmıştır.  
> FAZ 6 tarihi: 2026-07-07 · Canlı cutover ek doğrulama: 2026-07-12

---

## Ortam veri duruşu (2026-07-12)

| Kaynak | Mod | Doğrulama |
|--------|-----|----------|
| EPİAŞ | **live** | health + smoke |
| Weather | **live** | Open-Meteo |
| SCADA provider | **simulated** | EPİAŞ derived |
| Gemini LLM | **live** | `GET /health` → `data_hub.gemini` + models list ping |

Health yüzeyi: `weather` · `epias` · `scada` · `gemini`

Mimari: [SCADA-ADAPTER.md](./SCADA-ADAPTER.md) · Demo: [DEMO-RUNBOOK.md](./DEMO-RUNBOOK.md) · Release: [RELEASE-CHECKLIST.md](./RELEASE-CHECKLIST.md)

---

## Özet

| Senaryo | Durum | Otomatik test | Monitoring |
|---------|-------|---------------|------------|
| 6.1 EPİAŞ kapalı | **PASS** | Evet | Evet |
| 6.2 SCADA timeout / hata | **PASS** | Evet | Evet |
| 6.3 Weather API unavailable | **PASS** | Evet | Evet |
| 6.4 Drift oluştu | **PASS** | Evet | Evet |
| 6.5 Confidence düştü | **PASS** | Evet | Evet |
| 6.6 Recommendation değişti | **PASS** | Evet | Evet |
| 6.7 Alert oluştu | **PASS** | Evet | Evet |
| 6.8 Validation fail oldu | **PASS** | Evet | Evet |

**Genel RC durumu: PASS** — Tüm senaryolar mevcut kod + test + monitoring ile doğrulanmıştır.

---

## Doğrulama Kriterleri (Her Senaryo İçin)

| Kriter | Açıklama |
|--------|----------|
| Çalışıyor mu? | Pipeline veya ilgili modül beklenen davranışı üretiyor |
| Ölçülebilir mi? | Skor, oran, flag veya metadata alanında sayısal çıktı var |
| Monitoring görüyor mu? | `/api/v1/monitoring/*` veya pipeline metadata üzerinden izlenebilir |
| Testi var mı? | `tests/` altında otomatik pytest |
| Beklenen davranış | Roadmap'teki operasyonel beklentiyle uyumlu |

---

## Senaryo Matrisi

### 6.1 — EPİAŞ kapalı

| Alan | Detay |
|------|-------|
| **Durum** | **PASS** |
| **Beklenen davranış** | Canlı EPİAŞ erişilemez veya kimlik bilgisi yoksa mock fallback; neden telemetry'de görünür; pipeline tamamlanır |
| **Kod** | `modules/data_hub/epias.py`, `modules/data_hub/epias_auth.py` |
| **Testler** | `tests/test_epias_auth.py`, `tests/test_real_data_reliability.py`, `tests/test_phase2_integration.py` |
| **Monitoring** | `GET /monitoring/degraded-summary`, `GET /monitoring/observability-summary` → `fallback_reasons`, `source_success_rates.epias` |
| **Pipeline metadata** | `telemetry.sources.epias.mode=mock`, `reason` ∈ {`auth_failed`, `credentials_missing`, `mapping_failed`, `forced_mock`} |
| **Manuel smoke** | `.env` içinde `EPIAS_USE_MOCK=true` veya geçersiz credential ile pipeline tetikle; degraded-summary'de epias mock sayacı artmalı |

---

### 6.2 — SCADA timeout / hata (ve MVP simulator)

| Alan | Detay |
|------|-------|
| **Durum** | **PASS** |
| **Beklenen davranış** | (A) Fiziksel SCADA yok / `SCADA_USE_MOCK=true` + EPİAŞ canlı → `EpiasSimulatedScadaProvider`: `mode=simulated`, `source=simulated_from_epias`, `live=false`. (B) Live REST URL set ama istek düşerse → simulator veya son çare `mode=mock` (`reason=request_failed`). |
| **Kod** | `modules/data_hub/scada.py`, `modules/data_hub/scada_providers.py`, `modules/performance/service.py` |
| **Testler** | `tests/test_scada.py` (`test_scada_epias_simulator_scales_national_wind`, `test_scada_live_fallback_to_mock_on_error`, `test_scada_ping_reports_simulated_provider`) |
| **Monitoring** | `degraded-summary` → scada `simulated` veya `mock`; UI banner **Operational: EPİAŞ Derived (MW) · Equipment: Mock** |
| **Pipeline metadata** | `telemetry.sources.scada.mode` ∈ {`simulated`, `mock`, `live`} |
| **Manuel smoke** | `python scripts/smoke_gemini_scada_proxy.py` → `mode=simulated` |

---

### 6.3 — Weather API unavailable

| Alan | Detay |
|------|-------|
| **Durum** | **PASS** |
| **Beklenen davranış** | Open-Meteo başarısız → NASA POWER fallback; ikisi de başarısız → mock |
| **Kod** | `modules/data_hub/weather.py`, `modules/data_hub/nasa_power.py` |
| **Testler** | `tests/test_real_data_reliability.py::test_weather_open_meteo_failure_uses_nasa_power`, `tests/test_phase2_integration.py::test_open_meteo_balikesir` |
| **Monitoring** | `degraded-summary`, `observability-summary.fallback_reasons` |
| **Pipeline metadata** | `telemetry.sources.weather` mode/reason |
| **Manuel smoke** | Ağ kesintisi simülasyonu veya mock patch ile Open-Meteo hata; forecast adımı tamamlanmalı |

---

### 6.4 — Drift oluştu

| Alan | Detay |
|------|-------|
| **Durum** | **PASS** |
| **Beklenen davranış** | MAPE/maliyet sapması z-score veya legacy eşik ile drift flag; confidence kalibrasyonuna yansır |
| **Kod** | `modules/monitoring/drift.py`, `core/pipeline.py` |
| **Testler** | `tests/test_drift_detection.py` |
| **Monitoring** | `GET /monitoring/drift-summary` → `mape_drift_runs`, `severity_counts` |
| **Pipeline metadata** | `metadata.drift`, `log_model_metrics.drift` |
| **Manuel smoke** | Birkaç pipeline run sonrası drift-summary endpoint 200 + `version` dönmeli |

---

### 6.5 — Confidence düştü

| Alan | Detay |
|------|-------|
| **Durum** | **PASS** |
| **Beklenen davranış** | Yüksek MAPE ve drift confidence_stack içinde `confidence_calibrated` değerini düşürür; coverage hesaplanır |
| **Kod** | `modules/forecast/production/confidence_stack.py` |
| **Testler** | `tests/test_confidence_stack.py` |
| **Monitoring** | `GET /monitoring/confidence-stack`, `observability-summary.coverage` |
| **Pipeline metadata** | `confidence_stack.base_confidence`, `confidence_calibrated`, `coverage` |
| **Manuel smoke** | Pipeline sonrası confidence-stack endpoint `found=true` ve calibrated ≤ base (drift varsa) |

---

### 6.6 — Recommendation değişti

| Alan | Detay |
|------|-------|
| **Durum** | **PASS** |
| **Beklenen davranış** | Risk/MAPE/maliyet profiline göre action plan ve recommendation quality metrikleri güncellenir |
| **Kod** | `modules/recommendation/quality.py`, `modules/ai/assistant.py` |
| **Testler** | `tests/test_recommendation_quality.py`, `tests/test_decision_reliability.py` |
| **Monitoring** | `GET /monitoring/recommendation-quality` → `quality_score`, `action_coverage` |
| **Pipeline metadata** | `metadata.action_plan`, `recommendation_quality` |
| **Manuel smoke** | Farklı risk profilli run'larda recommendation-quality skorunun değiştiği doğrulanır |

---

### 6.7 — Alert oluştu

| Alan | Detay |
|------|-------|
| **Durum** | **PASS** |
| **Beklenen davranış** | Eşik aşımında WARNING/CRITICAL alert; alert quality precision ve false-negative proxy |
| **Kod** | `modules/alerting/service.py`, `modules/alerting/quality.py` |
| **Testler** | `tests/test_alerting_mape.py`, `tests/test_alert_quality.py` |
| **Monitoring** | `GET /monitoring/alert-quality` → `precision_proxy`, `false_negative_rate` |
| **Pipeline metadata** | `alert_status.severity`, `alert_quality` |
| **Manuel smoke** | Yüksek risk/MAPE ile pipeline; executive report `critical_alerts_count` ≥ 0 |

---

### 6.8 — Validation fail oldu

| Alan | Detay |
|------|-------|
| **Durum** | **PASS** |
| **Beklenen davranış** | Data Quality / Model Reliability / Decision Reliability gate fail → pipeline durur veya HTTP 422 |
| **Kod** | `core/data_quality.py`, `modules/forecast/production/model_reliability.py`, `modules/recommendation/decision_reliability.py` |
| **Testler** | `tests/test_data_quality.py`, `tests/test_model_reliability.py`, `tests/test_decision_reliability.py` |
| **Monitoring** | Gate durumu `observability.gates_passed`; başarısız run audit'te eksik adım |
| **Pipeline metadata** | `data_quality.gate_passed=false` veya exception |
| **Manuel smoke** | Duplicate timestamp ile DQ gate fail senaryosu (`test_duplicate_timestamps_fail_gate`) |

---

## Uçtan Uca Zincir Doğrulaması

| Akış | Test | Durum |
|------|------|-------|
| Pipeline 6 adım (0800→0805) | `tests/test_pipeline_architecture.py`, `tests/integration/test_full_pipeline.py` | **PASS** |
| Forecast → Reporting contract | `tests/integration/test_full_pipeline.py::test_full_pipeline_data_contract` | **PASS** |
| Tüm monitoring endpoint'leri | `tests/test_observability.py::test_monitoring_endpoints_exist` | **PASS** |
| Observability birleşik özet | `tests/test_observability.py::test_monitoring_observability_summary_endpoint` | **PASS** |

---

## Önerilen Yerel Doğrulama Komutu

```powershell
cd C:\Users\Burak\aerovantage
python scripts/smoke_demo.py
```

Geniş pytest seti:

```powershell
python -m pytest tests/test_observability.py tests/test_real_data_reliability.py tests/test_scada.py tests/test_drift_detection.py tests/test_confidence_stack.py tests/test_recommendation_quality.py tests/test_alert_quality.py tests/test_data_quality.py tests/test_model_reliability.py tests/integration/test_full_pipeline.py -v
```

Frontend kapıları (roadmap şablonu):

```powershell
cd frontend
npm run build
npx tsc --noEmit
npm run lint
```

---

## Açık Riskler (RC Sonrası)

| Risk | Etki | Not |
|------|------|-----|
| SCADA simülasyon ölçeği | Site-specific telemetri yok | Ulusal rüzgar → kapasite payı; gerçek SCADA gelince provider swap |
| Gemini kota / anahtar | AI insight fallback | Playbook `source=fallback`; pipeline devam eder |
| EPİAŞ credential sızıntısı | Hesap riski | Yalnızca `.env`; chat anahtarlarını yenile |
| Shell/CI ortamı | Otomatik pytest | `smoke_demo.py` yerel doğrulama |
| GitHub push / tag | Uzak senkron | Roadmap kapsamı dışı — [RELEASE-CHECKLIST.md](./RELEASE-CHECKLIST.md) |

---

## İmza

| Rol | Durum | Tarih |
|-----|-------|-------|
| FAZ 6 RC Verification | Tamamlandı | 2026-07-07 |
| FAZ 7 i18n | Tamamlandı | 2026-07-07 |
| Live cutover + SCADA simulator + Gemini | Doğrulandı | 2026-07-12 |
| Sonraki | Release checklist (push/tag kullanıcı onayıyla) | — |
