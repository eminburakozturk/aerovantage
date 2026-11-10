# Sprint 1B Engineering Standards

Bu dokuman AeroVantage v1.0 RC icin repository genelinde uygulanacak muhendislik standartlarini tanimlar.

## 1) Kod Standardi
- TypeScript-first: yeni kod `any` icermemeli, union/discriminated type tercih edilmeli.
- Fonksiyonlar tek sorumluluk ilkesine gore yazilmali; UI ve data access ayni fonksiyonda birlesmemeli.
- Erken return ve acik isimlendirme tercih edilmeli.

## 2) Dosya Standardi
- Feature/workspace dosyalari `src/app/*` ve `src/components/workspace/*` ekseninde tutulur.
- Altyapi ve paylasilan katmanlar `src/lib/*` altinda konumlanir.
- Yeni utility dosyalari tek amacli olmalidir.

## 3) Naming Standardi
- Bilesenler: `PascalCase`.
- Hooklar: `useXxx`.
- Utils/fonksiyonlar: `camelCase`.
- Constant map/sabitler: `UPPER_SNAKE_CASE` veya `CONST_OBJECT`.

## 4) Import Standardi
- Alias import (`@/...`) tercih edilir.
- Katman yonu korunur: app/components -> hooks/lib -> api/infrastructure.
- Dosya ici siralama: framework, external, internal.

## 5) TypeScript Standardi
- Public fonksiyonlarda donus tipi net olmali.
- Response/DTO tipleri `src/lib/api/types.ts` uzerinden paylasilmali.
- Sessiz `unknown` veya implicit `any` kabul edilmez.

## 6) ESLint Standardi
- Lint warning birikimi kabul edilmez.
- Yeni kod warning/noise olusturmadan merge edilmeli.
- Deprecated kullanimlar acik backlog maddesiyle azaltilmali.

## 7) Repository Kurallari
- Refactor adimlari kucuk ve geri alinabilir olmali.
- Her adimda backward compatibility korunmali.
- Sprint boyunca behavior parity zorunludur.

## 8) Folder Kurallari
- Workspace metadata tek kaynak: `src/lib/workspace-config.ts`.
- Core route metadata tek kaynak: `src/lib/routes.ts`.
- Navigation projection `src/components/layout/nav-config.ts` uzerinden uretilir.

## 9) Component Kurallari
- Presentation componentleri prop-driven olmali.
- Async state gorunumleri ortak primitive (`async-state`) uzerinden kullanilmali.
- Layout componentleri domain fetch yapmamalidir.

## 10) Service Kurallari
- API transport, endpoint ve orchestration ayrimi korunmali.
- API public surface sadece `src/lib/api.ts` uzerinden disariya acilmali.

## 11) Hook Kurallari
- Hooklar UI'dan bagimsiz test edilebilir saf davranisa yakin olmalidir.
- URL/search param mantigi ortak hooklarda merkezi tutulmalidir.

## 12) Utils Kurallari
- Utils deterministik ve yan etkisiz olmalidir.
- Ayni isi yapan duplicate util olusturulmamali; mevcut util genisletilmelidir.

## 13) AI Kod Standardlari
- AI recommendation/hint UI'lari tek gorunus dili kullanmalidir.
- AI response parsing logic'i UI katmaninda degil, lib/domain katmaninda tutulmalidir.
- Prompt/config degisiklikleri versiyonlu ve acik kayitla ilerlemelidir.

