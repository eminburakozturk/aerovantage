# AeroVantage Benutzerhandbuch (DE)

## Sprache wechseln

1. **Verwaltung** (`/settings`) oeffnen
2. Tab **Sprache** oder Panel in der Uebersicht waehlen
3. Tuerkisch / Englisch / Deutsch — ohne vollstaendigen Seitenreload
4. Einstellung wird in `localStorage` gespeichert

## Lokalisierte Bereiche

| Bereich | Verhalten |
|---------|-----------|
| Navigation, Tabs, Fehler | Sofortige UI-Aktualisierung |
| KI-Briefing | API-Antwort in gewaehlter Sprache |
| PDF / Excel | Beschriftungen in gewaehlter Sprache |

## API

```
GET /api/v1/ai/briefing?context=dashboard&asset_id=RES-BAL-01&locale=de
GET /api/v1/reporting/export/pdf?asset_id=RES-BAL-01&locale=de
```

## Installation

Siehe [README.de.md](../README.de.md)
