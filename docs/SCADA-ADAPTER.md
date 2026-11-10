# SCADA Adapter & Provider Architecture

## İlke

**SCADA adapter kaldırılmaz.** Operational Intelligence her zaman `ScadaClient` üzerinden **saatlik aktif güç (MW)** ister.

EPİAŞ ≠ SCADA. Bilinçli ayrım:

| Katman | Ne sağlar | Bugünkü kaynak |
|--------|-----------|----------------|
| **Operational (MW)** | Aktif güç, günlük enerji, CF | EPİAŞ Derived *veya* Live SCADA |
| **Equipment telemetry** | Pitch, yaw, sıcaklık, alarm | **Mock** (fiziksel SCADA yokken) |

EPİAŞ’tan **uydurulmaz:** türbin sıcaklığı, pitch, yaw, alarm kodu, titreşim.

```
EPİAŞ (ulusal rüzgar MW)          Gerçek SCADA (ileride)
        │                                    │
        ▼                                    ▼
EpiasSimulatedScadaProvider          LiveRestScadaProvider
        │                                    │
        └──────────┬─────────────────────────┘
                   ▼
            ScadaClient (adapter)
                   ▼
     Performance / Risk / OI  (MW only)
```

## Provider seçimi

| Koşul | Provider | `mode` | `live` | Operational | Equipment |
|-------|----------|--------|--------|-------------|-----------|
| `SCADA_API_URL` + `SCADA_USE_MOCK=false` | `LiveRestScadaProvider` | `live` | `true` | live | live |
| Fiziksel yok + EPİAŞ canlı | `EpiasSimulatedScadaProvider` | `simulated` | `false` | derived | mock |
| EPİAŞ da mock / hata | `DeterministicMockScadaProvider` | `mock` | `false` | mock | mock |

## Gözlemlenen saatler

`EpiasSimulatedScadaProvider` EPİAŞ’tan gelen saatleri `observed_hours` olarak işaretler; günün geri kalanı pad (0 MW) edilir ve **MAPE / risk maliyetine girmez**.

## Simülasyon güvenliği

`mode` ∈ {`simulated`,`mock`} iken:

- `evaluation_mode=simulation`, `mape_informational=true`
- Alert severity en fazla WARNING + `[Simülasyon]` öneki
- Rule Engine CRITICAL/WARNING → INFO (proxy ground truth)

## Metadata örneği

```json
{
  "mode": "simulated",
  "source": "simulated_from_epias",
  "confidence": "simulated",
  "live": "false",
  "label": "Operational: EPİAŞ Derived (MW) · Equipment: Mock",
  "operational_layer": "derived",
  "equipment_layer": "mock",
  "observed_hours": ["00:00", "01:00"],
  "padded_hours": ["08:00", "09:00"]
}
```

UI: **Operational: EPİAŞ Derived (MW) · Equipment: Mock**

## Dosyalar

- `modules/data_hub/scada.py` — adapter
- `modules/data_hub/scada_providers.py` — provider’lar
- `modules/data_hub/ground_truth.py` — proxy / observed helpers
