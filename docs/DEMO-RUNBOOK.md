# Demo Runbook — Staj / RC sunumu

Feature Freeze sonrası **gösterim paketi**. Yeni özellik yok; canlı EPİAŞ + Gemini + SCADA simulator ile Operational Intelligence anlatılır.

## 60 saniyelik hikâye

1. **Gerçek piyasa / şeffaflık verisi:** EPİAŞ TGT + PTF / realtime rüzgar.
2. **Gerçek meteoroloji:** Open-Meteo.
3. **SCADA katmanı mimaride duruyor** — fiziksel erişim yok; provider = EPİAŞ türevi simülatör.
4. **Karar katmanı:** Gemini canlı; hata olursa playbook fallback.
5. **Gelecek:** gerçek SCADA API → yalnızca provider değişir; OI aynı kalır.

Sunum cümlesi:

> “Gerçek SCADA erişimimiz olmadığı için bu katmanı mimariye uygun şekilde simüle ettik. Gerçek bir SCADA API’si sağlandığında yalnızca provider değişecek; sistemin geri kalanı aynı kalacak.”

## Önkoşul

| Öğe | Değer |
|-----|--------|
| `.env` | `EPIAS_USE_MOCK=false`, `WEATHER_USE_MOCK=false`, `SCADA_USE_MOCK=true`, `LLM_PROVIDER=gemini` |
| Backend | yeniden başlatılmış (settings cache) |
| Frontend | `http://localhost:3000` |

Credential’lar chat’te paylaşılmamalı; yalnızca `.env` (gitignored).

## Tek komut smoke

```powershell
cd C:\Users\Burak\aerovantage
python scripts/smoke_demo.py
```

Beklenen özet:

| Kontrol | Beklenen |
|---------|----------|
| EPİAŞ / Weather | live |
| SCADA | `simulated` / `simulated_from_epias` / `live=false` |
| Gemini | `source=gemini` |
| Unit | `tests/test_scada.py` yeşil |

## Canlı UI turu (≈5 dk)

1. **Operasyon** → pipeline **Tahmin** çalıştır.
2. Amber banner: **Operational: EPİAŞ Derived (MW) · Equipment: Mock**.
3. System Health: `epias`/`weather` live; `scada` = `simulated`.
4. **İzleme → Observability** — degraded/confidence panelleri.
5. **Yönetim → Dil** — tr / en / de geçişi.
6. **Yönetim → AI Modelleri** — Gemini live.

## Mimari diyagram (tahta)

```
EPİAŞ ──► EpiasSimulatedScadaProvider ──► ScadaClient ──► OI / Performance / Risk / AI
Open-Meteo ─────────────────────────────────────────────► Forecast
Gemini ─────────────────────────────────────────────────► Decision insight
```

İleride: `LiveRestScadaProvider` ← gerçek SCADA; üst katman değişmez.

## Dokümanlar

- [SCADA-ADAPTER.md](./SCADA-ADAPTER.md)
- [LIVE-DATA-CUTOVER.md](./LIVE-DATA-CUTOVER.md)
- [AI-ML-OPS.md](./AI-ML-OPS.md)
- [RC-VERIFICATION.md](./RC-VERIFICATION.md)
- [DEPLOYMENT.md](./DEPLOYMENT.md)

## Bilinçli sınırlar (dürüstçe söyle)

- SCADA **simüle** — gerçek türbin telemetrisi değil.
- Ulusal rüzgar → santral kapasitesine ölçek; site-specific değildir.
- Hybrid XGB artifact yoksa physics fallback olabilir.

## Otomatik yenileme (UI açıkken)

| Ne | Sıklık | Gerekçe |
|----|--------|---------|
| Dashboard / health | **10 dk** | Connector durumu taze; ağır LLM yok |
| Tam pipeline (EPİAŞ+Gemini) | **1 saat** | EPİAŞ PTF / realtime-generation **saatlik** tane |

Manuel **Tahmin** her an çalıştırılabilir.
