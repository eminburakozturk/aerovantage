# System Checkup — 2026-07-12

## Durum özeti

| Alan | Sonuç |
|------|--------|
| Smoke demo (önceki koşu) | Yeşil — EPİAŞ/Weather/Gemini live, SCADA simulated |
| Feature Freeze roadmap | Tamam |
| Bu checkup’ta düzeltilenler | Aşağıda |

## Bu turda yapılan düzeltmeler

1. **Güvenlik** — `frontend/src/lib/server/backend.ts`: `NEXT_PUBLIC_API_SECRET_KEY` fallback kaldırıldı (yalnızca `API_SECRET_KEY`).
2. **Gemini optimizasyon** — TTS/audio/embedding modelleri eleniyor; ListModels sonucu instance cache.
3. **AI rüzgar hızı** — Peak wind artık Open-Meteo’dan; reverse power-curve yalnız fallback.
4. **Health etiketleri** — weather/epias ping’e `live` + `label` eklendi.

## Bilinçli / beklenen

- SCADA **simulated** (fiziksel yok) — mimari doğru.
- System Health “warn/mockMode” SCADA simulated iken normal (tam live değil).
- Hybrid XGB artifact yoksa physics fallback olabilir.

## Senin kontrol listesi

```powershell
cd C:\Users\Burak\aerovantage

# 1) Birim testler
python -m pytest tests/test_scada.py tests/test_llm_health.py tests/test_data_quality.py tests/test_real_data_reliability.py -q

# 2) Canlı paket
python scripts/smoke_demo.py

# 3) Frontend (opsiyonel ama önerilir)
cd frontend
npx tsc --noEmit
npm run lint
```

UI:
1. Backend restart
2. Operasyon → Tahmin
3. Health: weather/epias/gemini live, scada simulated
4. AI insight `source=gemini` (fallback olmamalı)
5. `frontend/.env.local` içinde `API_SECRET_KEY` var mı? (`NEXT_PUBLIC_API_SECRET_KEY` olmamalı)

## Hâlâ açık (ürün / ops)

- Gerçek gerçek SCADA API
- Chat’te paylaşılmış credential rotasyonu
- Commit / push / tag (sen onaylayınca)
