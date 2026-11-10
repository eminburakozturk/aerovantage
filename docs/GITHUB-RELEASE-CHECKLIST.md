# GitHub Release Checklist — v1.0.0 RC1

> Push / tag yalnızca kullanıcı açıkça onaylarsa.

## Pre-push (kod / docs)

- [x] README complete (hero → contributing)
- [x] Screenshots under `docs/screenshots/`
- [x] LICENSE / SECURITY.md / CONTRIBUTING.md / CHANGELOG.md
- [x] `docs/architecture.md` current (Next.js + BFF)
- [x] `.gitignore` excludes `node_modules`, `.next`, `.env*`, `_checkup`, `video_frames`
- [x] No tracked `frontend/node_modules` / `.next` / `.env.local`
- [x] Version **v1.0.0 RC1** aligned in README / UI locale / CHANGELOG
- [x] Known Limitations documented
- [x] Sprint G1 tests green (see `docs/SPRINT-G1-FINAL-TEST-REPORT.md`)
- [x] Smoke: `python scripts/smoke_demo.py`

## Operator

- [ ] Review `git status` / diff (no secrets)
- [ ] Commit release prep
- [ ] Rotate shared credentials if needed
- [ ] `git push` + tag `v1.0.0-rc1`
- [ ] Publish GitHub Release notes (from CHANGELOG RC1)

## Score

**GitHub Ready: 88 / 100** (→ ~95 after successful push/tag)

Details: [SPRINT-G2-GITHUB-RELEASE-REPORT.md](./SPRINT-G2-GITHUB-RELEASE-REPORT.md)
