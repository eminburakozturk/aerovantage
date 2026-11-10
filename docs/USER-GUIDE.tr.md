# AeroVantage Kullanıcı Kılavuzu (TR)

## Dil Değiştirme

1. **Yönetim** (`/settings`) sayfasını açın
2. **Dil** sekmesine gidin veya Genel özetindeki dil panelini kullanın
3. Türkçe / English / Deutsch seçin — sayfa yenilenmeden uygulanır
4. Tercih `localStorage` içinde saklanır

## Ne Çevrilir?

| Alan | Davranış |
|------|----------|
| Menü, sekmeler, hata mesajları | Anında UI güncellemesi |
| AI brifing paneli | Seçilen dilde API yanıtı |
| PDF / Excel rapor | Export sırasında seçilen dil |

## API

```
GET /api/v1/ai/briefing?context=dashboard&asset_id=RES-BAL-01&locale=en
GET /api/v1/reporting/export/pdf?asset_id=RES-BAL-01&locale=de
```

## Kurulum

Bkz. [README.tr.md](../README.tr.md)
