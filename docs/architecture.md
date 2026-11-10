# AeroVantage Mimari Dokümantasyonu

## Genel Bakış

AeroVantage, **modüler monolit** bir Operational Intelligence platformudur.
Birincil kullanıcı arayüzü **Next.js**; API **FastAPI**; iş mantığı `modules/` + `core/` içindedir.

`dashboard/` (Streamlit) **legacy** profilidir; ürün yüzeyi değildir.

## Katman Diyagramı

```
┌────────────────────────────────────────────────────────────┐
│  frontend/ (Next.js App Router)                            │
│  UI + BFF: /api/backend/[...path]  (server-only auth)      │
└──────────────────────────┬─────────────────────────────────┘
                           │ HTTP + Bearer (server)
┌──────────────────────────▼─────────────────────────────────┐
│  api/ (FastAPI)                                            │
│  Routing only — iş mantığı yok                             │
└──────────────────────────┬─────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────┐
│  modules/*  (forecast, market, risk, reporting, ai, …)     │
└──────────────────────────┬─────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────┐
│  core/  (pipeline, config, i18n, storage, data quality)    │
└────────────────────────────────────────────────────────────┘
```

### Veri / AI bağlayıcıları

```
EPİAŞ ──► EpiasSimulatedScadaProvider ──► ScadaClient ──► OI
Open-Meteo ────────────────────────────────────────────► Forecast
Gemini ────────────────────────────────────────────────► AI insight
         (fallback: playbook)
```

## Bağımlılık Kuralları

| Katman | İzin |
|--------|------|
| `frontend/` | HTTP → API (BFF). Python modül import **yasak** |
| `api/` | `modules/*`, `core/*` |
| `modules/*` | `core/*` + ilgili domain importları |
| `core/` | Standart kütüphane + pydantic / paylaşılmış yardımcılar |
| `dashboard/` (legacy) | Yalnızca HTTP — opsiyonel Docker profile |

## Docker

`docker-compose.yml`:

- **frontend** — port `3000`
- **api** — port `8000`
- **dashboard** — profile `legacy` (Streamlit)

## Günlük pipeline

1. Forecast (weather + production model)
2. Performance / sapma
3. Risk skoru + dengesizlik maliyeti
4. Alerts / rules
5. AI insight (Gemini veya playbook)
6. UI / reporting okur pipeline geçmişi

## Sürüm

**v1.0.0 RC1** — EPİAŞ + weather canlı; SCADA simüle; LLM Gemini (fallback playbook).
