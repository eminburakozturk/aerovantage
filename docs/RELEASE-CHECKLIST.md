# Release Checklist (RC1)

> **Maintenance Mode active.** AeroVantage v1.x development cycle is closed (`v1.0.0-rc1`).  
> Policy: [`V1-MAINTENANCE-POLICY.md`](V1-MAINTENANCE-POLICY.md) · Ideas: [`V2-BACKLOG.md`](V2-BACKLOG.md) · Next focus: [`HYPER-CORE.md`](HYPER-CORE.md).  
> Roadmap: GitHub push / tag / release **yalnızca kullanıcı açıkça isterse**.  
> Bu checklist RC1 hygiene + G5 release execution hazırlığını izler.

## 0) Güvenlik

> ### Credential Rotation Required Before Production
> RC1 is **not** production-credential-ready. Operators **must** rotate EPİAŞ / Gemini / `API_SECRET_KEY` and attest via `docs/CREDENTIAL-ROTATE.md` before any production or external live cutover. Shipping code does not imply rotated secrets.

- [x] `.env` gitignored (`git check-ignore` / `.gitignore`)
- [ ] **Credential Rotation Required Before Production** — EPİAŞ / Gemini / API Bearer rotated + attestation signed (manuel) — bkz. `docs/CREDENTIAL-ROTATE.md`
- [ ] Chat’te paylaşılmış EPİAŞ / Gemini anahtarları **operatör tarafından yenilenmiş** (manuel) — bkz. `docs/CREDENTIAL-ROTATE.md`
- [x] Frontend’de `NEXT_PUBLIC_API_SECRET_KEY` yok; BFF server-only
- [x] `frontend/.env.local` **tracked değil** (index’ten çıkarıldı + ignore)
- [x] `API_SECRET_KEY` **fail-closed** — boş varsayılan yok (`core/config.py`, BFF, compose `:?`, dashboard RuntimeError); örnekler boş
- [x] Eski `aerovantage-local-dev-key` runtime kaynaklarından kaldırıldı (2026-07-14)

## 1) Repository hygiene

- [x] `frontend/node_modules` untracked
- [x] `frontend/.next` untracked
- [x] `_checkup/` / `video_frames/` ignore + kaldırıldı
- [x] Dead components temizliği
- [x] LICENSE / SECURITY.md / CONTRIBUTING.md
- [x] README EN/TR/DE + Known Limitations + screenshots
- [x] `docs/architecture.md` Next.js + BFF
- [x] Version strings → **v1.0.0-rc1** (README / CHANGELOG / package.json / UI badge / release notes)
- [x] CHANGELOG RC1
- [x] Release notes `docs/RELEASE-NOTES-v1.0.0-rc1.md`
- [x] Maintenance Mode + Hyper Core transition docs (G5)

## 2) Veri / AI duruşu

- [ ] Root `.env`: `EPIAS_USE_MOCK=false`, `WEATHER_USE_MOCK=false`, `SCADA_USE_MOCK=true`, `LLM_PROVIDER=gemini` (ortam bağımlı)
- [ ] Backend restart sonrası settings cache temiz
- [x] `python scripts/smoke_demo.py` → yeşil (2026-07-14 RC1 cleanup)

## 3) Kalite kapıları

```powershell
python scripts/smoke_demo.py
python -m pytest tests/test_scada.py tests/test_observability.py tests/test_i18n.py -q
cd frontend
npm run lint
npx tsc --noEmit
npm run build
```

- [x] Frontend lint / tsc / build yeşil (2026-07-14)
- [x] Backend observability + scada/i18n/reporting pytest yeşil (G1 weather mock TZ fix)

## 4) Manuel UI (DEMO-RUNBOOK)

- [ ] Operasyon → pipeline → amber SCADA banner
- [ ] Health: epias/weather live, scada simulated
- [ ] Observability
- [ ] Dil tr / en / de
- [ ] AI Models: Gemini live

## 5) Docker (opsiyonel)

- [ ] `docker compose up --build`
- [ ] UI + `/health` OK

## 6) GitHub / tag (G5)

1. [x] Local annotated tag `v1.0.0-rc1` (Sprint G5)
2. [ ] Push tag to `origin` (only if remote + auth work)
3. [ ] GitHub Release via `gh release create` (prep notes ready; needs `gh` auth)

## İmza

| Kontrol | Tarih | Not |
|---------|-------|-----|
| Smoke | 2026-07-14 | G5 re-validation (see Final Release Report) |
| Frontend gates | 2026-07-14 | lint / tsc / build — G5 |
| Observability pytest | 2026-07-14 | G5 suite |
| Release tag | 2026-07-14 | `v1.0.0-rc1` local |
| GitHub Release | — | Prep-only until `gh` available |
| Maintenance Mode | 2026-07-14 | Active |
