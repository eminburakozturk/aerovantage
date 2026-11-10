# AeroVantage User Guide (EN)

## Changing Language

1. Open **Administration** (`/settings`)
2. Go to the **Language** tab or use the panel on the Overview tab
3. Select Turkish / English / German — applied without full page reload
4. Preference is stored in `localStorage`

## What Is Localized?

| Area | Behavior |
|------|----------|
| Navigation, tabs, errors | Instant UI update |
| AI briefing panel | API response in selected language |
| PDF / Excel export | Labels and summary in selected language |

## API

```
GET /api/v1/ai/briefing?context=dashboard&asset_id=RES-BAL-01&locale=en
GET /api/v1/reporting/export/pdf?asset_id=RES-BAL-01&locale=de
```

## Installation

See [README.md](../README.md)
