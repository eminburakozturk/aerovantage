# Live Data Cutover (Sprint B)

## Bu ortamın politikası

| Kaynak | Mod | Not |
|--------|-----|-----|
| EPİAŞ | **live** | TGT auth doğrulandı |
| Weather | **live** | Open-Meteo doğrulandı |
| SCADA adapter | **korunur** | OI her zaman `ScadaClient` kullanır |
| SCADA provider (MVP) | **simulated** | `EpiasSimulatedScadaProvider` — EPİAŞ'tan türetilmiş |
| LLM | **gemini** | `LLM_PROVIDER=gemini` |

Ayrıntılı mimari: [SCADA-ADAPTER.md](./SCADA-ADAPTER.md)

**Doğrulama:** `python scripts/smoke_demo.py`  
(veya `python scripts/smoke_gemini_scada_proxy.py`)  
Beklenen SCADA meta: `mode=simulated`, `source=simulated_from_epias`, `live=false`.

## Smoke test

```powershell
cd C:\Users\Burak\aerovantage
python scripts/smoke_demo.py
```

Ayrıntılı UI turu: [DEMO-RUNBOOK.md](./DEMO-RUNBOOK.md) · Release: [RELEASE-CHECKLIST.md](./RELEASE-CHECKLIST.md)

## UI doğrulama

1. Backend'i yeniden başlatın (`.env` değişince şart).
2. Pipeline çalıştırın.
3. Operasyon merkezinde amber banner: **Operational: EPİAŞ Derived (MW) · Equipment: Mock**
4. System Health’te scada satırı `simulated` (live değil).

## Güvenlik

- Credential'lar yalnızca kök `.env` içinde tutulur; commit edilmez.
- Chat'te paylaşılan anahtarları yenileyin.
