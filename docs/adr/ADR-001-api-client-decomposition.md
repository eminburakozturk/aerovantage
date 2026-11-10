# ADR-001: API Client Decomposition

## Problem
`frontend/src/lib/api.ts` tek dosyada config, auth transport, error handling, DTO/type tanımları, endpoint çağrıları, export/download akışı ve dashboard composition mantığını bir arada tutuyordu. Bu yapı bakım maliyetini artırıyor ve değişiklik riskini büyütüyordu.

## Karar
API istemcisi `frontend/src/lib/api/` altında katmanlara ayrıldı:
- `config.ts`
- `errors.ts`
- `transport.ts`
- `types.ts`
- `endpoints.ts`
- `downloads.ts`
- `dashboard.ts`
- `index.ts`

Public arayüz korunması için `frontend/src/lib/api.ts` dosyası backward-compatible entrypoint olarak bırakıldı (`export * from "./api"`).

## Gerekçe
- Sorumlulukların ayrılması ile okunabilirlik artar.
- Değişikliklerin etki alanı küçülür.
- Test ve doğrulama sınırları netleşir.
- Dış API davranışı değişmeden refactor yapılabilir.

## Sonuç
- Dış import sözleşmesi korunmuştur (`@/lib/api`).
- İç mimari modüler hale gelmiştir.
- Teknik borç kontrollü şekilde azaltılmıştır.
