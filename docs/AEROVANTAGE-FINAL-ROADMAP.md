# AeroVantage — Final Development Roadmap

> **Bu doküman AeroVantage'ın son geliştirme roadmap'idir.**  
> Bundan sonra yeni roadmap üretilmez. Tüm geliştirme yalnızca bu plandaki maddelere göre yapılır.  
> GitHub, release, push, deployment ve yayın hazırlıkları bu roadmap'in **kapsamı dışındadır** (ayrı süreç).  
> **v1.x Feature Complete + Maintenance Mode:** FAZ 1–7 tamam; v1.x geliştirme döngüsü **kapandı** (`v1.0.0-rc1`). Sonrası bakım/güvenlik/kalite — [`V1-MAINTENANCE-POLICY.md`](V1-MAINTENANCE-POLICY.md). Yeni ürün fikirleri → [`V2-BACKLOG.md`](V2-BACKLOG.md). Birincil gelecek odak → [`HYPER-CORE.md`](HYPER-CORE.md).

---

## Durum

| Alan | Durum |
|------|--------|
| Feature Freeze | **AKTİF** — yeni özellik yok |
| UI Freeze | **AKTİF** — yeni ekran/UX yok (FAZ 7 i18n istisna) |
| Maintenance Mode | **AKTİF** — v1.x development cycle closed (`v1.0.0-rc1`) |
| Primary focus | **Hyper Core** — [`HYPER-CORE.md`](HYPER-CORE.md) |
| Sprint amacı | Teknik olgunluk + operasyonel güvenilirlik (tarihsel) |
| Varsayılan dil | Türkçe (`tr`) |
| Desteklenen diller | `tr`, `en`, `de` |

---

## Sprint Kuralları (Her Adım İçin Zorunlu)

Her iş **küçük**, **bağımsız** ve **build alınabilir** olacak.

**Sonraki adıma geçmeden önce tüm kapılar yeşil olmalı:**

| Kapı | Komut / Kontrol |
|------|-----------------|
| Build | `cd frontend && npm run build` |
| TypeScript | `cd frontend && npx tsc --noEmit` |
| Lint | `cd frontend && npm run lint` |
| İlgili testler | `python -m pytest <ilgili-test-dosyaları> -v` |
| Manual Smoke Test | İlgili akışın elle doğrulanması |

**Her adım sonunda rapor** (aşağıdaki şablon).

**Kapsam dışı (bu roadmap boyunca yapılmaz):**

- Yeni özellik / yeni modül (FAZ maddeleri dışında)
- UI/UX değişikliği (FAZ 7 i18n hariç)
- GitHub push / release / tag
- Deployment / Docker / CI/CD yayın süreci
- Production Auth Hardening (`NEXT_PUBLIC_API_SECRET_KEY` — tamamlandı: BFF `/api/backend`)
- Canlı müşteri ortamı entegrasyonu

---

## Adım Rapor Şablonu

Her faz alt-adımı tamamlandığında yalnızca şu formatta rapor verilir:

```
• Amaç
• Yapılan değişiklikler
• Değişen dosyalar
• Test sonuçları
• Ölçülebilir metrikler
• Açık kalan riskler
• Sonraki adım
```

**Hiçbir faz tamamlanmadan sonraki faza geçilmez.**

---

## Mevcut Durum Özeti (Başlangıç Noktası)

Sprint 3 + PH ile büyük ölçüde tamamlanan altyapı (doğrulama ve sertleştirme gerekir):

| Faz | Tamamlanma | Not |
|-----|------------|-----|
| FAZ 1 | 100% | Telemetry, meta, NASA POWER fallback, freshness tamamlandı |
| FAZ 2 | 100% | DQ score, outlier, duplicate, pipeline gate tamamlandı |
| FAZ 3 | 100% | Walk-forward, model reliability gate, pipeline enforce tamamlandı |
| FAZ 4 | 100% | Decision gate, FN analizi, risk/SHAP doğrulama tamamlandı |
| FAZ 5 | 100% | Observability summary, pipeline latency/metrics, endpoint doğrulama tamamlandı |
| FAZ 6 | 100% | RC senaryo matrisi `docs/RC-VERIFICATION.md` ile tamamlandı |
| FAZ 7 | 100% | i18n altyapısı, tr/en/de UI, AI/export locale, README üç dil |

---

# FAZ 1 — REAL DATA RELIABILITY

**Öncelik:** En yüksek  
**Amaç:** Sistemin mümkün olduğunca mock veriden kurtulması.

## Yapılacaklar

### EPİAŞ
- [x] **1.1** Production mapping tamamlama ve doğrulama
- [x] **1.2** Gerçek response parse katmanı testleri
- [x] **1.3** Mock fallback yalnızca hata durumunda
- [x] **1.4** Mock kullanım oranı telemetry ile ölçüm

### SCADA
- [x] **1.5** Production adapter (Influx/REST) standardizasyon doğrulama
- [x] **1.6** Mock/Real state açık üretim (`mode`, `reason`)

### Weather
- [x] **1.7** Open-Meteo entegrasyonu gözden geçirme
- [x] **1.8** NASA POWER entegrasyonu doğrulama
- [x] **1.9** Veri kaynağı freshness kontrolü

## Done Criteria

- [x] Gerçek veri başarılı geldiğinde mock kullanılmamalı
- [x] Mock kullanıldıysa nedeni telemetry'de görünmeli
- [x] Monitoring ekranı gerçek veri / mock ayrımını göstermeli (mevcut UI — yalnızca doğrulama)

## İlgili Dosyalar

`modules/data_hub/epias.py`, `modules/data_hub/scada.py`, `modules/data_hub/weather.py`, `core/pipeline.py`, `api/routes/monitoring.py`

---

# FAZ 2 — DATA QUALITY

**Amaç:** Yanlış veri sisteme girmemeli.

## Yapılacaklar

- [x] **2.1** Data Contract doğrulama (mevcut `core/data_contracts.py` sertleştirme)
- [x] **2.2** Versioned contract uygulama kontrolü
- [x] **2.3** Feature Schema tek kaynak doğrulama
- [x] **2.4** Completeness kontrolü
- [x] **2.5** Timeliness kontrolü
- [x] **2.6** Consistency kontrolü
- [x] **2.7** Duplicate detection
- [x] **2.8** Missing value detection
- [x] **2.9** Outlier detection
- [x] **2.10** Data Quality Score hesaplama
- [x] **2.11** Pipeline öncesi Data Quality Gate (fail-fast)

## Done Criteria

- [x] Her pipeline çalışmadan önce Data Quality Gate geçmek zorunda

## İlgili Dosyalar

`core/data_contracts.py`, `modules/forecast/production/feature_schema.py`, `core/pipeline.py`, `tests/test_data_validation.py`

---

# FAZ 3 — MODEL RELIABILITY

**Amaç:** Tahmin motorunun güvenilir hale gelmesi.

## Yapılacaklar

- [x] **3.1** Train/Serve feature parity doğrulama
- [x] **3.2** Leakage tamamen kaldırılmış doğrulama
- [x] **3.3** Time series validation
- [x] **3.4** Walk-forward validation
- [x] **3.5** Acceptance gate
- [x] **3.6** Promotion rule
- [x] **3.7** Drift detection doğrulama
- [x] **3.8** Confidence stack doğrulama
- [x] **3.9** Prediction interval doğrulama
- [x] **3.10** Coverage hesaplama doğrulama

## Done Criteria

- [x] Hiçbir model validation geçmeden production pipeline'a alınmayacak

## İlgili Dosyalar

`modules/forecast/production/validation.py`, `feature_schema.py`, `confidence_stack.py`, `modules/monitoring/drift.py`, `xgb_hybrid_model.py`

---

# FAZ 4 — DECISION RELIABILITY

**Amaç:** Operational Intelligence katmanını doğrulamak.

## Yapılacaklar

- [x] **4.1** Recommendation quality ölçüm doğrulama
- [x] **4.2** Recommendation tutarlılık doğrulama
- [x] **4.3** Alert quality ölçüm doğrulama
- [x] **4.4** False positive oranı
- [x] **4.5** False negative analizi
- [x] **4.6** Risk score doğrulama
- [x] **4.7** Decision causality doğrulama
- [x] **4.8** Explainability (SHAP) gerçek model üzerinden doğrulama

## Done Criteria

- [x] AI kararları gerçek model çıktılarıyla uyumlu olmalı

## İlgili Dosyalar

`modules/recommendation/`, `modules/alerting/quality.py`, `modules/forecast/production/explainability.py`, `modules/ai/`

---

# FAZ 5 — OBSERVABILITY

**Amaç:** Sistemin her davranışı izlenebilir olmalı.

## Endpoint Doğrulama

- [x] **5.1** `GET /monitoring/degraded-summary`
- [x] **5.2** `GET /monitoring/drift-summary`
- [x] **5.3** `GET /monitoring/recommendation-quality`
- [x] **5.4** `GET /monitoring/alert-quality`
- [x] **5.5** `GET /monitoring/confidence-stack`
- [x] **5.6** `GET /monitoring/model-attribution`
- [x] **5.7** `GET /monitoring/decision-causality`
- [x] **5.8** `GET /monitoring/model-registry`
- [x] **5.9** `GET /monitoring/experiments/{id}` + `/experiments/latest/{asset_id}`

## Pipeline Metrics Genişletme

- [x] **5.10** Fallback sebepleri
- [x] **5.11** Source başarı oranı
- [x] **5.12** API başarı oranı
- [x] **5.13** Latency
- [x] **5.14** Coverage

## Done Criteria

- [x] Hiçbir kritik olay monitoring dışında kalmayacak
- [x] Mevcut monitoring UI metrikleri gösteriyor (doğrulama — yeni UI yok)

---

# FAZ 6 — RELEASE CANDIDATE VERIFICATION

**Amaç:** Mevcut capability'lerin uçtan uca doğrulanması. **Yeni kod yok.**

Her capability için kontrol:

- Çalışıyor mu?
- Ölçülebilir mi?
- Monitoring görüyor mu?
- Testi var mı?
- Beklenen davranışı gösteriyor mu?

## Senaryo Matrisi

- [x] **6.1** EPİAŞ kapalı
- [x] **6.2** SCADA timeout
- [x] **6.3** Weather API unavailable
- [x] **6.4** Drift oluştu
- [x] **6.5** Confidence düştü
- [x] **6.6** Recommendation değişti
- [x] **6.7** Alert oluştu
- [x] **6.8** Validation fail oldu

## Done Criteria

- [x] Tüm senaryolar dokümante edilmiş pass/fail ile işaretli
- [x] `docs/RC-VERIFICATION.md` oluşturulmuş

---

# FAZ 7 — INTERNATIONALIZATION (i18n)

**Amaç:** UI, AI çıktıları, export ve temel dokümantasyon tek kaynak çeviri sistemi ile yönetilsin.

**Desteklenen diller:** `tr` (varsayılan), `en`, `de`

## Kapsam

### UI (mevcut ekranlar — yeni ekran yok)
Sidebar, header, dashboard, operations, forecast, risk, monitoring, reports, settings, error/empty/loading, tooltip, status, butonlar, formlar

### AI
Executive summary, technical analysis, recommendation, action plan, alert explanation — seçilen dilde üretim

### Dokümantasyon
```
README.md       → English (ana — GitHub standardı)
README.tr.md    → Türkçe
README.de.md    → Deutsch
```
+ User Guide, Installation, Architecture, Deployment, API docs (üç dil)

### Export
PDF/rapor çıktıları seçilen dilde

## Teknik Kurallar

- Hardcoded UI string yasak
- Merkezi locale dosyaları: `frontend/src/locales/{tr,en,de}/`
- Dil değişimi sayfa yenilemeden (client-side)
- Yeni anahtar ekleme zorunlu (gelecek için kural; bu fazda mevcut UI migrate)
- Fransızca/İspanyolca **eklenmeyecek**

## Alt Adımlar

- [x] **7.1** i18n altyapısı (`next-intl` veya eşdeğer)
- [x] **7.2** Locale dosya yapısı + dil switcher (mevcut settings)
- [x] **7.3** Core UI string migration (tr/en/de)
- [x] **7.4** AI prompt dil parametresi
- [x] **7.5** PDF/export dil desteği
- [x] **7.6** README.tr.md + README.de.md + README.md (EN) güncelleme
- [x] **7.7** Temel docs üç dil

## Done Criteria

- [x] Üç dil arasında anlık geçiş çalışıyor
- [x] AI çıktıları seçilen dilde
- [x] PDF/raporlar seçilen dilde
- [x] README üç dilde mevcut

---

## Uygulama Sırası (Kilitli)

```
FAZ 1 → FAZ 2 → FAZ 3 → FAZ 4 → FAZ 5 → FAZ 6 → FAZ 7
```

GitHub / release / push → **Tüm fazlar bittikten sonra** (ayrı süreç).

---

## Agent Talimatı (Cursor / AI)

1. Bu dosyayı tek kaynak kabul et.
2. Yeni roadmap veya sprint planı üretme.
3. Feature freeze — yalnızca bu plandaki `[ ]` maddeleri işle (FAZ 1–7 tamam; yeni özellik yok).
4. v1.x’te yalnızca bakım politikasına uygun işler; yeni fikirleri `docs/V2-BACKLOG.md`’ye yaz (`docs/V1-MAINTENANCE-POLICY.md`).
5. Her adım sonunda kalite kapılarını çalıştır ve rapor ver.
6. GitHub/push/release konularına girme (kullanıcı söyleyene kadar).
7. Soru sorma — kullanıcı yönlendirecek (`geç`, `1.1`, vb.).

---

*Son güncelleme: 2026-07-07 — AeroVantage Final Roadmap v1.0.0*
