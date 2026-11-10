# AI / ML Operations (Sprint G)

## Current policy (this environment)

| Component | Mode | Notes |
|-----------|------|-------|
| Decision AI | **gemini (live)** | `LLM_PROVIDER=gemini` + `LLM_API_KEY` (`AQ.` auth key destekli) |
| Hybrid XGB | artifact / physics fallback | Train: `scripts/train_hybrid_models.py` |
| Model registry | on-disk | `GET /api/v1/monitoring/model-registry` |
| SCADA provider | **simulated** | Fiziksel SCADA yok → `EpiasSimulatedScadaProvider` |
| SCADA adapter | unchanged | OI hâlâ `ScadaClient` kullanır |

Playbook fallback: Gemini hata verirse insight `source=fallback` ile playbook’a düşer; pipeline çökmez.

## Smoke

```powershell
cd C:\Users\Burak\aerovantage
python scripts/smoke_ai_ml.py
python scripts/smoke_gemini_scada_proxy.py
# veya hepsi:
python scripts/smoke_demo.py
```

Beklenen: Gemini `source=gemini`, SCADA `mode=simulated` / `source=simulated_from_epias`.

## Enable / switch LLM

1. Root `.env`:

```env
LLM_PROVIDER=gemini   # veya openai | mock
LLM_API_KEY=...
```

2. Backend’i yeniden başlat (`aero stop` / `aero start` veya tray)
3. **Yönetim → AI Modelleri**: live / ready
4. `python scripts/smoke_gemini_scada_proxy.py`

## Retrain / promote (hybrid model)

```powershell
python scripts/train_hybrid_models.py
```

Promotion yalnızca `deployable` adaylarda. İncele:

- `GET /api/v1/monitoring/model-registry`
- `GET /api/v1/monitoring/experiments/latest/{asset_id}`

## Operator checklist

- [ ] Settings → AI Models: provider + key
- [ ] Pipeline 0804 → `action_plan` + Gemini insight
- [ ] Observability: confidence / recommendation panelleri
- [ ] Banner: **Operational: EPİAŞ Derived (MW) · Equipment: Mock** (yüksek MAPE ≠ santral arızası; bilgisel)
- [ ] Otomatik yenileme: dashboard **10 dk**, tam pipeline **1 saat** (EPİAŞ saatlik tane)
- [ ] Mimari: gerçek SCADA gelince yalnızca `SCADA_API_URL` + `SCADA_USE_MOCK=false`

Ayrıntı: [SCADA-ADAPTER.md](./SCADA-ADAPTER.md) · [DEMO-RUNBOOK.md](./DEMO-RUNBOOK.md)
